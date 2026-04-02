"""Solve-playtest packet generation and scoring helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from random import Random
from typing import Any

from app.scoring.blind_review import (
    _load_benchmark_holdout,
    _load_generated_top_k,
    _shuffled_board_view,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _balanced_board_order(
    generated: list[dict[str, Any]],
    benchmark: list[dict[str, Any]],
    *,
    tester_count: int,
    boards_per_tester: int,
    rng: Random,
) -> list[list[dict[str, Any]]]:
    tester_packets: list[list[dict[str, Any]]] = [[] for _ in range(tester_count)]
    generated_index = 0
    benchmark_index = 0
    for tester_index in range(tester_count):
        used_ids: set[str] = set()
        while len(tester_packets[tester_index]) < boards_per_tester:
            source_pool = generated if len(tester_packets[tester_index]) % 2 == 0 else benchmark
            source_index = generated_index if source_pool is generated else benchmark_index
            if not source_pool:
                source_pool = benchmark if source_pool is generated else generated
                source_index = benchmark_index if source_pool is benchmark else generated_index
            if not source_pool:
                break
            candidate = source_pool[source_index % len(source_pool)]
            board_id = str(candidate["source_board_id"])
            if board_id in used_ids and len(used_ids) < len(generated) + len(benchmark):
                if source_pool is generated:
                    generated_index += 1
                else:
                    benchmark_index += 1
                continue
            tester_packets[tester_index].append(candidate)
            used_ids.add(board_id)
            if source_pool is generated:
                generated_index += 1
            else:
                benchmark_index += 1
        rng.shuffle(tester_packets[tester_index])
    return tester_packets


def build_solve_playtest_packet(
    *,
    run_dir: Path,
    normalized_dir: Path,
    output_dir: Path,
    tester_count: int,
    boards_per_tester: int,
    seed: int,
) -> dict[str, Any]:
    """Create deterministic source-hidden solve-playtest packets."""

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = Random(seed)
    generated = _load_generated_top_k(run_dir)
    benchmark = _load_benchmark_holdout(normalized_dir)
    rng.shuffle(generated)
    rng.shuffle(benchmark)
    tester_sources = _balanced_board_order(
        generated,
        benchmark,
        tester_count=tester_count,
        boards_per_tester=boards_per_tester,
        rng=rng,
    )

    key_entries: list[dict[str, Any]] = []
    tester_packets: list[dict[str, Any]] = []
    counter = 1
    for tester_index, boards in enumerate(tester_sources, start=1):
        tester_id = f"tester_{tester_index:02d}"
        packet_boards: list[dict[str, Any]] = []
        for item in boards:
            packet_board_id = f"playtest_board_{counter:03d}"
            counter += 1
            board_words, solution_groups = _shuffled_board_view(item, seed=seed)
            packet_boards.append(
                {
                    "packet_board_id": packet_board_id,
                    "board_words": board_words,
                    "group_count": len(solution_groups),
                }
            )
            key_entries.append(
                {
                    "packet_board_id": packet_board_id,
                    "tester_id": tester_id,
                    "hidden_source": {
                        "source_label": item["source_label"],
                        "source_board_id": item["source_board_id"],
                        "source_run_id": item["source_run_id"],
                    },
                    "solution_groups": solution_groups,
                }
            )
        tester_packets.append({"tester_id": tester_id, "boards": packet_boards})

    packet_payload = {
        "seed": seed,
        "tester_count": tester_count,
        "boards_per_tester": boards_per_tester,
        "tester_packets": tester_packets,
        "notes": [
            "Solve-playtest packets hide each board's source.",
            "Board word order is deterministically shuffled.",
        ],
    }
    key_payload = {"entries": key_entries}

    _write_json(output_dir / "solve_playtest_packet.json", packet_payload)
    _write_json(output_dir / "solve_playtest_key.json", key_payload)
    (output_dir / "solve_playtest_instructions.md").write_text(
        "\n".join(
            [
                "# Solve Playtest Instructions",
                "",
                "- Solve each board without looking up the answer key.",
                "- Record whether you solved it, how many mistakes you made, "
                "and whether it felt fair.",
                "- Use the CSV template to log one row per board.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with (output_dir / "solve_playtest_template.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tester_id",
                "packet_board_id",
                "solved",
                "mistake_count",
                "fairness_rating",
                "naturalness_rating",
                "publishable",
                "notes",
            ],
        )
        writer.writeheader()
    return packet_payload


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            return [dict(row) for row in payload.get("responses", [])]
        return [dict(row) for row in payload]
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _parse_yes_no(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def score_solve_playtest(
    *,
    packet_key_path: Path,
    response_paths: list[Path],
    output_dir: Path,
) -> dict[str, Any]:
    """Aggregate solve-playtest responses."""

    output_dir.mkdir(parents=True, exist_ok=True)
    key_payload = json.loads(packet_key_path.read_text())
    source_by_packet_id = {
        entry["packet_board_id"]: entry["hidden_source"]["source_label"]
        for entry in key_payload.get("entries", [])
    }

    rows: list[dict[str, Any]] = []
    for path in response_paths:
        rows.extend(_load_rows(path))

    generated_rows = [
        row for row in rows if source_by_packet_id.get(row.get("packet_board_id")) == "generated"
    ]
    benchmark_rows = [
        row for row in rows if source_by_packet_id.get(row.get("packet_board_id")) == "benchmark"
    ]

    def _publishable_rate(items: list[dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return round(
            sum(1 for item in items if _parse_yes_no(item.get("publishable"))) / len(items),
            4,
        )

    summary = {
        "response_count": len(rows),
        "generated_publishable_rate": _publishable_rate(generated_rows),
        "benchmark_publishable_rate": _publishable_rate(benchmark_rows),
        "solved_rate": round(
            sum(1 for row in rows if _parse_yes_no(row.get("solved"))) / max(len(rows), 1),
            4,
        ),
    }
    payload = {
        "summary": summary,
        "notes": [
            "Solve-playtest summaries are descriptive and do not replace the blind-review gate."
        ],
    }
    _write_json(output_dir / "solve_playtest_results.json", payload)
    (output_dir / "solve_playtest_results.md").write_text(
        "\n".join(
            [
                "# Solve Playtest Results",
                "",
                f"- Responses: {summary['response_count']}",
                f"- Solved rate: {summary['solved_rate']:.3f}",
                f"- Generated publishable rate: {summary['generated_publishable_rate']:.3f}",
                f"- Benchmark publishable rate: {summary['benchmark_publishable_rate']:.3f}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload
