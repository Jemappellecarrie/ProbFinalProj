"""Helpers for deterministic final-quality funnel reporting."""

from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from typing import Any

from app.core.editorial_quality import (
    record_editorial_family_signature,
    record_editorial_flags,
    record_surface_wordplay_family_signatures,
    record_theme_family_signatures,
)
from app.features.semantic_baseline import normalize_signal
from app.schemas.evaluation_models import CandidatePoolPuzzleRecord
from app.utils.ids import stable_id


def board_signature(record: CandidatePoolPuzzleRecord) -> str:
    """Return a stable board-level signature ignoring tile order."""

    return stable_id("board", sorted(normalize_signal(word) for word in record.board_words))


def solution_signature(record: CandidatePoolPuzzleRecord) -> str:
    """Return a stable solution-level signature for one candidate board."""

    groups = [
        {
            "label": normalize_signal(label),
            "words": sorted(normalize_signal(word) for word in words),
        }
        for label, words in zip(record.group_labels, record.group_word_sets, strict=True)
    ]
    return stable_id("solution", sorted(groups, key=lambda item: (item["label"], item["words"])))


def mechanism_signature(record: CandidatePoolPuzzleRecord) -> str:
    """Return a simple mechanism-mix signature for grouping diagnostics."""

    return "+".join(sorted(record.mechanism_mix_summary))


def _decision_counts(records: list[CandidatePoolPuzzleRecord]) -> Counter[str]:
    counts = Counter({"accept": 0, "borderline": 0, "reject": 0})
    for record in records:
        counts[str(record.verification_decision or "reject")] += 1
    return counts


def _unique_count(records: list[CandidatePoolPuzzleRecord]) -> int:
    return len({board_signature(record) for record in records})


def _unique_family_count(records: list[CandidatePoolPuzzleRecord]) -> int:
    return len({record_editorial_family_signature(record) for record in records})


def _warning_flag_breakdown(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    counts = Counter(flag for record in records for flag in record.warnings)
    return dict(sorted(counts.items()))


def _reject_reason_breakdown(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    counts = Counter(reason for record in records for reason in record.reject_reasons)
    return dict(sorted(counts.items()))


def _top_cooccurring_reject_reasons(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    pair_counts: Counter[str] = Counter()
    for record in records:
        reasons = sorted(set(record.reject_reasons))
        for left, right in combinations(reasons, 2):
            pair_counts[f"{left}+{right}"] += 1
    return dict(sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))[:10])


def _mechanism_mix_by_decision(
    records: list[CandidatePoolPuzzleRecord],
) -> dict[str, dict[str, int]]:
    payload: dict[str, Counter[str]] = {
        "accept": Counter(),
        "borderline": Counter(),
        "reject": Counter(),
    }
    for record in records:
        decision = str(record.verification_decision or "reject")
        payload.setdefault(decision, Counter())[mechanism_signature(record)] += 1
    return {decision: dict(sorted(counts.items())) for decision, counts in sorted(payload.items())}


def _mechanism_family_breakdown(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    counts = Counter()
    for record in records:
        if record.mixed_board:
            counts["mixed"] += 1
        elif set(record.group_types) == {"semantic"}:
            counts["semantic_only"] += 1
        else:
            counts["single_type_other"] += 1
        if "phonetic" in record.group_types:
            counts["phonetic_inclusive"] += 1
    return dict(sorted(counts.items()))


def _duplicate_signature_breakdown(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    counts = Counter(board_signature(record) for record in records)
    return dict(sorted((key, value) for key, value in counts.items() if value > 1))


def _family_repetition_histogram(records: list[CandidatePoolPuzzleRecord]) -> dict[str, int]:
    counts = Counter(record_editorial_family_signature(record) for record in records)
    return dict(sorted((key, value) for key, value in counts.items() if value > 1))


def _repeated_theme_family_count(records: list[CandidatePoolPuzzleRecord]) -> int:
    counts = Counter(
        signature for record in records for signature in record_theme_family_signatures(record)
    )
    return sum(1 for count in counts.values() if count > 1)


def _repeated_surface_wordplay_family_count(records: list[CandidatePoolPuzzleRecord]) -> int:
    counts = Counter(
        signature
        for record in records
        for signature in record_surface_wordplay_family_signatures(record)
    )
    return sum(1 for count in counts.values() if count > 1)


def _formulaic_board_rate(records: list[CandidatePoolPuzzleRecord]) -> float:
    return round(
        sum("formulaic_mixed_template" in record_editorial_flags(record) for record in records)
        / max(len(records), 1),
        4,
    )


def _repeated_family_rate(records: list[CandidatePoolPuzzleRecord]) -> float:
    family_counts = Counter(record_editorial_family_signature(record) for record in records)
    return round(
        sum(family_counts[record_editorial_family_signature(record)] > 1 for record in records)
        / max(len(records), 1),
        4,
    )


def _collapse_diagnostics(
    records: list[CandidatePoolPuzzleRecord],
    top_review_candidates: list[CandidatePoolPuzzleRecord],
) -> dict[str, Any]:
    if not records:
        return {
            "top_board_signature_share": 0.0,
            "top_mechanism_signature_share": 0.0,
            "top_solution_signature_share": 0.0,
            "top_editorial_family_share": 0.0,
            "repeated_top_k_pattern_count": 0,
        }

    board_counts = Counter(board_signature(record) for record in records)
    solution_counts = Counter(solution_signature(record) for record in records)
    mechanism_counts = Counter(mechanism_signature(record) for record in records)
    family_counts = Counter(record_editorial_family_signature(record) for record in records)
    top_k_duplicates = len(top_review_candidates) - len(
        {board_signature(record) for record in top_review_candidates}
    )
    total = len(records)
    return {
        "top_board_signature_share": round(max(board_counts.values()) / total, 4),
        "top_solution_signature_share": round(max(solution_counts.values()) / total, 4),
        "top_mechanism_signature_share": round(max(mechanism_counts.values()) / total, 4),
        "top_editorial_family_share": round(max(family_counts.values()) / total, 4),
        "repeated_top_k_pattern_count": top_k_duplicates,
    }


def _request_diagnostic_totals(request_diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    structurally_valid = sum(
        int(item.get("evaluated_combination_count", 0)) for item in request_diagnostics
    )
    invalid_reason_counts = Counter()
    for item in request_diagnostics:
        invalid_reason_counts.update(item.get("rejected_combination_reason_counts", {}))
    structurally_invalid = sum(invalid_reason_counts.values())
    return {
        "structurally_valid_count": structurally_valid,
        "structurally_invalid_count": structurally_invalid,
        "structurally_invalid_reason_breakdown": dict(sorted(invalid_reason_counts.items())),
    }


def _diagnosis_notes(report: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    collapse = report["collapse_diagnostics"]
    if report["top_k_unique_count"] < min(20, max(report["top_review_candidate_count"], 1)):
        notes.append("Top-review candidate pool is still narrow after dedupe.")
    if collapse["top_board_signature_share"] >= 0.5:
        notes.append("Selection is collapsing onto a repeated board family.")
    if collapse["top_editorial_family_share"] >= 0.35:
        notes.append("Editorial family repetition is still dominating the candidate pool.")
    if collapse["top_mechanism_signature_share"] >= 0.75:
        notes.append("Mechanism mix is concentrated in a narrow family of boards.")
    if report["rejected_count"] > (report["accepted_count"] + report["borderline_count"]):
        notes.append(
            "Verifier/scoring pressure is rejecting more persisted candidates than it keeps."
        )
    if not notes:
        notes.append("No dominant collapse mode crossed the report heuristics.")
    return notes


def build_funnel_report(
    *,
    total_generation_requests: int,
    candidate_records: list[CandidatePoolPuzzleRecord],
    top_review_candidates: list[CandidatePoolPuzzleRecord],
    request_diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic funnel report for the final-quality sprint."""

    decision_counts = _decision_counts(candidate_records)
    duplicate_signature_breakdown = _duplicate_signature_breakdown(candidate_records)
    request_totals = _request_diagnostic_totals(request_diagnostics)
    total_puzzle_candidates_seen = (
        request_totals["structurally_valid_count"] + request_totals["structurally_invalid_count"]
    )
    selected_records = [record for record in candidate_records if record.selected]
    top_k_unique_count = len({board_signature(record) for record in top_review_candidates})
    top_k_unique_family_count = _unique_family_count(top_review_candidates)

    report = {
        "total_generation_requests": total_generation_requests,
        "persisted_candidate_count": len(candidate_records),
        "selected_board_count": len(selected_records),
        "top_review_candidate_count": len(top_review_candidates),
        "total_puzzle_candidates_seen": total_puzzle_candidates_seen,
        "structurally_valid_count": request_totals["structurally_valid_count"],
        "structurally_invalid_count": request_totals["structurally_invalid_count"],
        "structurally_invalid_reason_breakdown": request_totals[
            "structurally_invalid_reason_breakdown"
        ],
        "unique_board_count": _unique_count(candidate_records),
        "unique_family_count": _unique_family_count(candidate_records),
        "duplicate_board_count": sum(duplicate_signature_breakdown.values())
        - len(duplicate_signature_breakdown),
        "duplicate_signature_breakdown": duplicate_signature_breakdown,
        "family_repetition_histogram": _family_repetition_histogram(candidate_records),
        "selected_unique_board_count": _unique_count(selected_records),
        "accepted_count": decision_counts["accept"],
        "borderline_count": decision_counts["borderline"],
        "rejected_count": decision_counts["reject"],
        "accepted_unique_count": _unique_count(
            [record for record in candidate_records if record.verification_decision == "accept"]
        ),
        "borderline_unique_count": _unique_count(
            [record for record in candidate_records if record.verification_decision == "borderline"]
        ),
        "rejected_unique_count": _unique_count(
            [record for record in candidate_records if record.verification_decision == "reject"]
        ),
        "decision_percentages": {
            "accept": round(decision_counts["accept"] / max(len(candidate_records), 1), 4),
            "borderline": round(decision_counts["borderline"] / max(len(candidate_records), 1), 4),
            "reject": round(decision_counts["reject"] / max(len(candidate_records), 1), 4),
        },
        "reject_reason_breakdown": _reject_reason_breakdown(candidate_records),
        "warning_flag_breakdown": _warning_flag_breakdown(candidate_records),
        "top_cooccurring_reject_reasons": _top_cooccurring_reject_reasons(candidate_records),
        "mechanism_mix_by_decision": _mechanism_mix_by_decision(candidate_records),
        "mechanism_family_breakdown": _mechanism_family_breakdown(candidate_records),
        "top_k_unique_count": top_k_unique_count,
        "top_k_unique_family_count": top_k_unique_family_count,
        "repeated_theme_family_count": _repeated_theme_family_count(candidate_records),
        "repeated_surface_wordplay_family_count": _repeated_surface_wordplay_family_count(
            candidate_records
        ),
        "formulaic_board_rate": _formulaic_board_rate(candidate_records),
        "repeated_family_rate": _repeated_family_rate(candidate_records),
        "collapse_diagnostics": _collapse_diagnostics(candidate_records, top_review_candidates),
    }
    report["diagnosis_notes"] = _diagnosis_notes(report)
    return report


def funnel_report_markdown(report: dict[str, Any]) -> str:
    """Render a compact human-readable funnel report."""

    lines = [
        "# Final Quality Funnel Report",
        "",
        f"- Generation requests: {report['total_generation_requests']}",
        f"- Puzzle candidates seen: {report['total_puzzle_candidates_seen']}",
        (
            f"- Structural validity: {report['structurally_valid_count']} valid / "
            f"{report['structurally_invalid_count']} invalid"
        ),
        (
            f"- Persisted candidate pool: {report['persisted_candidate_count']} "
            f"({report['unique_board_count']} unique boards)"
        ),
        f"- Unique editorial families: {report['unique_family_count']}",
        (
            f"- Decisions: accept={report['accepted_count']}, "
            f"borderline={report['borderline_count']}, reject={report['rejected_count']}"
        ),
        f"- Top-review unique boards: {report['top_k_unique_count']}",
        f"- Top-review unique families: {report['top_k_unique_family_count']}",
        f"- Formulaic board rate: {report['formulaic_board_rate']:.4f}",
        f"- Repeated-family rate: {report['repeated_family_rate']:.4f}",
        "",
        "## Collapse Diagnostics",
        (
            f"- Top board signature share: "
            f"{report['collapse_diagnostics']['top_board_signature_share']:.4f}"
        ),
        (
            f"- Top mechanism signature share: "
            f"{report['collapse_diagnostics']['top_mechanism_signature_share']:.4f}"
        ),
        (
            f"- Top editorial family share: "
            f"{report['collapse_diagnostics']['top_editorial_family_share']:.4f}"
        ),
        (
            f"- Duplicate signatures: "
            f"{json.dumps(report['duplicate_signature_breakdown'], sort_keys=True)}"
        ),
        "",
        "## Notes",
    ]
    lines.extend(f"- {note}" for note in report["diagnosis_notes"])
    return "\n".join(lines) + "\n"
