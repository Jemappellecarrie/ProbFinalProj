"""Blind review packet generation and scoring helpers."""

from __future__ import annotations

import csv
import json
from itertools import combinations
from pathlib import Path
from random import Random
from typing import Any

from app.schemas.benchmark_models import (
    BlindReviewAnswerKey,
    BlindReviewAnswerKeyEntry,
    BlindReviewHiddenSource,
    BlindReviewPacket,
    BlindReviewPacketBundle,
    BlindReviewPacketEntry,
    BlindReviewScoringSummary,
    BlindReviewSolutionGroup,
    QualityGateResult,
)
from app.schemas.evaluation_models import AcceptedPuzzleRecord, TopKSummary
from app.scoring.benchmark_audit import load_normalized_benchmark

REVIEW_FIELDS = [
    "unique_clear_grouping",
    "fair_not_forced",
    "labels_feel_natural",
    "aha_satisfaction",
    "publishable",
    "notes",
]
FAILURE_MODE_KEYWORDS = {
    "ambiguity": ("ambiguous", "ambiguity", "unclear", "multiple"),
    "forced": ("forced",),
    "labels": ("label", "labels", "unnatural"),
    "satisfaction": ("aha", "satisfying", "satisfaction"),
    "trivia": ("trivia", "obscure"),
}


def _read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _load_generated_top_k(run_dir: Path) -> list[dict[str, Any]]:
    top_k = TopKSummary.model_validate(_read_json(run_dir / "top_k.json"))
    accepted_lookup = {
        record.puzzle_id: record
        for record in [
            AcceptedPuzzleRecord.model_validate(item)
            for item in list(_read_json(run_dir / "accepted.json"))
        ]
    }
    candidates: list[dict[str, Any]] = []
    for ranked in sorted(top_k.ranked_puzzles, key=lambda item: (item.rank, item.puzzle_id)):
        accepted = accepted_lookup.get(ranked.puzzle_id)
        group_word_sets = (
            accepted.group_word_sets if accepted is not None else ranked.group_word_sets
        )
        group_labels = accepted.group_labels if accepted is not None else ranked.group_labels
        if not group_word_sets:
            raise ValueError(
                "Generated review packet requires group_word_sets in accepted.json or top_k.json."
            )
        candidates.append(
            {
                "source_label": "generated",
                "source_board_id": ranked.puzzle_id,
                "source_run_id": str((_read_json(run_dir / "summary.json"))["run_id"]),
                "board_words": list(
                    accepted.board_words if accepted is not None else ranked.board_words
                ),
                "solution_groups": [
                    {"label": label, "words": list(words)}
                    for label, words in zip(group_labels, group_word_sets, strict=True)
                ],
            }
        )
    return candidates


def _load_benchmark_holdout(normalized_dir: Path) -> list[dict[str, Any]]:
    boards = load_normalized_benchmark(normalized_dir)
    holdout_payload = dict(_read_json(normalized_dir / "holdout_split.json"))
    holdout_ids = set(holdout_payload.get("board_ids", []))
    candidates: list[dict[str, Any]] = []
    for board in boards:
        if board.benchmark_board_id not in holdout_ids:
            continue
        candidates.append(
            {
                "source_label": "benchmark",
                "source_board_id": board.benchmark_board_id,
                "source_run_id": None,
                "board_words": list(board.board_words),
                "solution_groups": [
                    {"label": group.group_label, "words": list(group.words)}
                    for group in board.groups
                ],
            }
        )
    return sorted(candidates, key=lambda item: item["source_board_id"])


def _deterministic_sample(
    items: list[dict[str, Any]],
    *,
    sample_size: int,
    rng: Random,
) -> list[dict[str, Any]]:
    if sample_size >= len(items):
        return list(items)
    indices = sorted(rng.sample(range(len(items)), sample_size))
    return [items[index] for index in indices]


def _shuffled_board_view(
    item: dict[str, Any],
    *,
    seed: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    board_words = list(item["board_words"])
    group_rows = [dict(group) for group in item["solution_groups"]]
    board_rng = Random(f"{seed}:{item['source_label']}:{item['source_board_id']}:board")
    board_rng.shuffle(board_words)
    group_rng = Random(f"{seed}:{item['source_label']}:{item['source_board_id']}:groups")
    group_rng.shuffle(group_rows)
    for row in group_rows:
        word_rng = Random(f"{seed}:{row['label']}")
        word_rng.shuffle(row["words"])
    return board_words, group_rows


def build_blind_review_packet(
    *,
    run_dir: Path,
    normalized_dir: Path,
    output_dir: Path,
    generated_count: int,
    benchmark_count: int,
    seed: int,
) -> BlindReviewPacketBundle:
    """Create a deterministic mixed blind-review packet."""

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = Random(seed)
    generated_candidates = _deterministic_sample(
        _load_generated_top_k(run_dir),
        sample_size=generated_count,
        rng=rng,
    )
    benchmark_candidates = _deterministic_sample(
        _load_benchmark_holdout(normalized_dir),
        sample_size=benchmark_count,
        rng=rng,
    )
    combined = generated_candidates + benchmark_candidates
    rng.shuffle(combined)

    packet_entries: list[BlindReviewPacketEntry] = []
    answer_key_entries: list[BlindReviewAnswerKeyEntry] = []
    for index, item in enumerate(combined, start=1):
        packet_board_id = f"blind_board_{index:03d}"
        board_words, solution_groups = _shuffled_board_view(item, seed=seed)
        packet_entries.append(
            BlindReviewPacketEntry(
                packet_board_id=packet_board_id,
                review_order=index,
                board_words=board_words,
                solution_groups=[
                    BlindReviewSolutionGroup(label=group["label"], words=group["words"])
                    for group in solution_groups
                ],
                review_fields=REVIEW_FIELDS,
            )
        )
        answer_key_entries.append(
            BlindReviewAnswerKeyEntry(
                packet_board_id=packet_board_id,
                hidden_source=BlindReviewHiddenSource(
                    source_label=item["source_label"],
                    source_board_id=item["source_board_id"],
                    source_run_id=item["source_run_id"],
                ),
            )
        )

    packet = BlindReviewPacket(
        packet_name=f"blind_review_seed_{seed}",
        seed=seed,
        entries=packet_entries,
        notes=[
            "Reviewer-facing packet hides each board's source.",
            "Board word order and solution-group order are deterministically shuffled.",
            (
                f"Requested {generated_count + benchmark_count} boards and used "
                f"{len(packet_entries)} available boards."
            ),
            (
                "Shortfall: unable to supply the full requested packet size "
                "from the available board pool."
                if (
                    len(generated_candidates) < generated_count
                    or len(benchmark_candidates) < benchmark_count
                )
                else "No packet shortfall for the requested sample sizes."
            ),
        ],
    )
    answer_key = BlindReviewAnswerKey(packet_name=packet.packet_name, entries=answer_key_entries)

    packet_json_path = output_dir / "blind_review_packet.json"
    packet_csv_path = output_dir / "blind_review_packet.csv"
    reviewer_template_path = output_dir / "reviewer_template.csv"
    answer_key_path = output_dir / "blind_review_key.json"
    instructions_path = output_dir / "blind_review_instructions.md"
    _write_json(packet_json_path, packet.model_dump(mode="json"))
    _write_json(answer_key_path, answer_key.model_dump(mode="json"))
    _write_packet_csv(packet_csv_path, packet)
    _write_packet_csv(reviewer_template_path, packet)
    instructions_path.write_text(_blind_review_instructions(packet), encoding="utf-8")

    return BlindReviewPacketBundle(
        packet=packet,
        answer_key=answer_key,
        output_files={
            "packet_json": str(packet_json_path),
            "packet_csv": str(packet_csv_path),
            "reviewer_template": str(reviewer_template_path),
            "answer_key": str(answer_key_path),
            "instructions": str(instructions_path),
        },
    )


def _write_packet_csv(path: Path, packet: BlindReviewPacket) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "packet_board_id",
                "review_order",
                "board_words",
                "solution_groups",
                *REVIEW_FIELDS,
            ],
        )
        writer.writeheader()
        for entry in packet.entries:
            writer.writerow(
                {
                    "packet_board_id": entry.packet_board_id,
                    "review_order": entry.review_order,
                    "board_words": " | ".join(entry.board_words),
                    "solution_groups": " || ".join(
                        f"{group.label}: {', '.join(group.words)}"
                        for group in entry.solution_groups
                    ),
                    "unique_clear_grouping": "",
                    "fair_not_forced": "",
                    "labels_feel_natural": "",
                    "aha_satisfaction": "",
                    "publishable": "",
                    "notes": "",
                }
            )


def _blind_review_instructions(packet: BlindReviewPacket) -> str:
    return (
        "\n".join(
            [
                "# Blind Review Instructions",
                "",
                f"- Packet: `{packet.packet_name}`",
                f"- Boards: {len(packet.entries)}",
                "- Review each board without trying to infer its source.",
                "- Fill in one row per board using either the CSV or JSON template.",
                "- Required fields:",
                "  - unique_clear_grouping: yes / no",
                "  - fair_not_forced: 1-5",
                "  - labels_feel_natural: 1-5",
                "  - aha_satisfaction: 1-5",
                "  - publishable: yes / no",
                "  - notes: optional free text",
            ]
        )
        + "\n"
    )


def _load_review_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = _read_json(path)
        if isinstance(payload, dict):
            rows = payload.get("reviews", [])
        else:
            rows = payload
        return [dict(row) for row in rows]

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _parse_yes_no(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _pairwise_publishable_agreement(rows: list[dict[str, Any]]) -> float:
    reviewer_lookup: dict[str, dict[str, bool]] = {}
    for row in rows:
        reviewer_id = str(row.get("reviewer_id", "")).strip()
        if not reviewer_id:
            continue
        reviewer_lookup.setdefault(reviewer_id, {})[str(row["packet_board_id"])] = _parse_yes_no(
            row.get("publishable")
        )

    pair_scores = []
    for left, right in combinations(sorted(reviewer_lookup), 2):
        shared = sorted(set(reviewer_lookup[left]) & set(reviewer_lookup[right]))
        if not shared:
            continue
        matches = sum(
            1
            for board_id in shared
            if reviewer_lookup[left][board_id] == reviewer_lookup[right][board_id]
        )
        pair_scores.append(matches / len(shared))
    if not pair_scores:
        return 0.0
    return round(sum(pair_scores) / len(pair_scores), 4)


def _failure_modes(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in FAILURE_MODE_KEYWORDS}
    for row in rows:
        if _parse_yes_no(row.get("publishable")):
            continue
        notes = str(row.get("notes", "")).lower()
        for mode, keywords in FAILURE_MODE_KEYWORDS.items():
            if any(keyword in notes for keyword in keywords):
                counts[mode] += 1
    return {key: value for key, value in counts.items() if value > 0}


def score_blind_review(
    *,
    answer_key_path: Path,
    review_paths: list[Path],
    output_dir: Path,
) -> BlindReviewScoringSummary:
    """Aggregate completed blind review forms into publishable-rate results."""

    output_dir.mkdir(parents=True, exist_ok=True)
    answer_key = BlindReviewAnswerKey.model_validate(_read_json(answer_key_path))
    source_by_packet_id = {
        entry.packet_board_id: entry.hidden_source.source_label for entry in answer_key.entries
    }

    rows: list[dict[str, Any]] = []
    for path in review_paths:
        rows.extend(_load_review_rows(path))

    rows = [row for row in rows if str(row.get("packet_board_id", "")).strip()]
    publishable_votes: dict[str, list[bool]] = {}
    for row in rows:
        publishable_votes.setdefault(str(row["packet_board_id"]), []).append(
            _parse_yes_no(row.get("publishable"))
        )

    reviewed_generated = 0
    reviewed_benchmark = 0
    majority_generated = 0
    majority_benchmark = 0
    for packet_board_id, votes in publishable_votes.items():
        source = source_by_packet_id.get(packet_board_id)
        majority_publishable = sum(votes) > (len(votes) / 2)
        if source == "generated":
            reviewed_generated += 1
            majority_generated += int(majority_publishable)
        elif source == "benchmark":
            reviewed_benchmark += 1
            majority_benchmark += int(majority_publishable)

    generated_rate = (
        round(majority_generated / reviewed_generated, 4) if reviewed_generated else None
    )
    benchmark_rate = (
        round(majority_benchmark / reviewed_benchmark, 4) if reviewed_benchmark else 0.0
    )
    if reviewed_generated == 0:
        gate = QualityGateResult(
            gate_name="generated_publishable_majority_40_percent",
            threshold_rate=0.4,
            actual_rate=None,
            passed=None,
            resolved=False,
            evaluated_board_count=0,
            notes=[
                "No completed generated-board reviews were provided.",
                "The final 40% gate remains unresolved until real reviewer forms are scored.",
            ],
        )
    else:
        gate = QualityGateResult(
            gate_name="generated_publishable_majority_40_percent",
            threshold_rate=0.4,
            actual_rate=generated_rate,
            passed=generated_rate is not None and generated_rate >= 0.4,
            resolved=True,
            evaluated_board_count=reviewed_generated,
            notes=[
                "Board publishable status is determined by reviewer majority vote.",
                "Ties count as not publishable.",
            ],
        )
    summary = BlindReviewScoringSummary(
        generated_publishable_rate=generated_rate or 0.0,
        benchmark_publishable_rate=benchmark_rate,
        inter_rater_agreement={
            "publishable_pairwise_agreement": _pairwise_publishable_agreement(rows)
        },
        failure_modes=_failure_modes(rows),
        final_quality_gate=gate,
    )

    results_json_path = output_dir / "blind_review_results.json"
    results_markdown_path = output_dir / "blind_review_results.md"
    gate_json_path = output_dir / "final_quality_gate.json"
    gate_markdown_path = output_dir / "final_quality_gate.md"
    _write_json(results_json_path, summary.model_dump(mode="json"))
    _write_json(gate_json_path, gate.model_dump(mode="json"))
    results_markdown_path.write_text(_blind_review_results_markdown(summary), encoding="utf-8")
    gate_markdown_path.write_text(_final_quality_gate_markdown(gate), encoding="utf-8")
    summary.output_files.update(
        {
            "results_json": str(results_json_path),
            "results_markdown": str(results_markdown_path),
            "final_quality_gate": str(gate_json_path),
            "final_quality_gate_markdown": str(gate_markdown_path),
        }
    )
    return summary


def _blind_review_results_markdown(summary: BlindReviewScoringSummary) -> str:
    gate_status = (
        "UNRESOLVED"
        if not summary.final_quality_gate.resolved
        else ("PASS" if summary.final_quality_gate.passed else "FAIL")
    )
    generated_rate = (
        "unresolved"
        if summary.final_quality_gate.actual_rate is None
        else f"{summary.generated_publishable_rate:.3f}"
    )
    return (
        "\n".join(
            [
                "# Blind Review Results",
                "",
                f"- Generated publishable rate: {generated_rate}",
                f"- Benchmark publishable rate: {summary.benchmark_publishable_rate:.3f}",
                (
                    f"- Pairwise publishable agreement: "
                    f"{
                        summary.inter_rater_agreement.get(
                            'publishable_pairwise_agreement', 0.0
                        ):.3f}"
                ),
                (f"- Final gate `{summary.final_quality_gate.gate_name}`: {gate_status}"),
            ]
        )
        + "\n"
    )


def _final_quality_gate_markdown(gate: QualityGateResult) -> str:
    status = "UNRESOLVED" if not gate.resolved else ("PASS" if gate.passed else "FAIL")
    actual_rate = "unresolved" if gate.actual_rate is None else f"{gate.actual_rate:.3f}"
    return (
        "\n".join(
            [
                "# Final Quality Gate",
                "",
                f"- Gate: `{gate.gate_name}`",
                f"- Threshold: {gate.threshold_rate:.3f}",
                f"- Actual rate: {actual_rate}",
                f"- Evaluated generated boards: {gate.evaluated_board_count}",
                f"- Status: {status}",
            ]
        )
        + "\n"
    )
