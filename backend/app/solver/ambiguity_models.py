"""Ambiguity scaffold helpers.

Role in pipeline:
    Convert baseline solver disagreement signals into structured ambiguity
    evidence that can flow through verification, traces, and batch evaluation.

Inputs:
    - `PuzzleCandidate`
    - `EnsembleSolverResult`

Outputs:
    - `AmbiguityReport`

Why core logic is intentionally deferred:
    Real leakage estimation, alternative partition search, and ambiguity
    thresholds are project-defining heuristics and remain human-owned.

Acceptance criteria:
    - Demo mode emits typed ambiguity evidence.
    - Evidence can be inspected without claiming it is final-quality reasoning.
"""

from __future__ import annotations

from itertools import combinations

from app.schemas.evaluation_models import (
    AlternativeGroupingCandidate,
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    CrossGroupCompatibility,
    EnsembleSolverResult,
    WordGroupLeakage,
)
from app.schemas.puzzle_models import PuzzleCandidate
from app.utils.ids import new_id


def _target_group_label_by_word(puzzle: PuzzleCandidate) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in puzzle.groups:
        for word in group.words:
            mapping[word] = group.label
    return mapping


def build_mock_ambiguity_report(
    puzzle: PuzzleCandidate,
    ensemble_result: EnsembleSolverResult | None,
) -> AmbiguityReport:
    """Build a deterministic placeholder ambiguity report from ensemble disagreement.

    This report is intentionally shallow and transparent. It exists to exercise
    traces, summaries, and debug flows while leaving real ambiguity reasoning
    to the human-owned evaluator.
    """

    if ensemble_result is None:
        return AmbiguityReport(
            evaluator_name="baseline_ambiguity_evaluator",
            risk_level=AmbiguityRiskLevel.LOW,
            penalty_hint=0.0,
            reject_recommended=False,
            summary="No ensemble data was available; ambiguity scaffold reports low risk by default.",
            notes=[
                "This baseline report is incomplete without ensemble disagreement data.",
            ],
            metadata={"baseline_only": True},
        )

    target_labels = _target_group_label_by_word(puzzle)
    alternative_groupings: list[AlternativeGroupingCandidate] = []
    leakage_records: list[WordGroupLeakage] = []
    compatibility_records: list[CrossGroupCompatibility] = []
    compatibility_keys: set[tuple[str, str]] = set()

    for vote in ensemble_result.votes:
        if not vote.alternative_solution_proposed or not vote.proposed_groups:
            continue

        total_words = sum(len(group) for group in vote.proposed_groups)
        matching_words = 0
        for group in vote.proposed_groups:
            for word in group:
                if word in target_labels:
                    matching_words += 1

        alternative_groupings.append(
            AlternativeGroupingCandidate(
                candidate_id=new_id("alt_grouping"),
                source_solver=vote.solver_name,
                proposed_groups=vote.proposed_groups,
                matched_target_solution=vote.matched_target_solution,
                overlap_ratio=round(matching_words / max(total_words, 1), 3),
                notes=[
                    "Alternative grouping candidate captured from a baseline ensemble vote.",
                ],
                metadata={"baseline_only": True},
            )
        )

        for proposed_group in vote.proposed_groups:
            target_group_labels = sorted(
                {target_labels[word] for word in proposed_group if word in target_labels}
            )
            if len(target_group_labels) <= 1:
                continue

            target_group_label = target_group_labels[0]
            for word in proposed_group:
                source_group_label = target_labels.get(word)
                if source_group_label is None or source_group_label == target_group_label:
                    continue
                leakage_records.append(
                    WordGroupLeakage(
                        word=word,
                        source_group_label=source_group_label,
                        target_group_label=target_group_label,
                        leakage_kind="alternative_grouping_overlap",
                        evidence_strength=0.2,
                        notes=[
                            "Word appeared in a mixed alternative group proposed by a baseline solver.",
                        ],
                        metadata={"source_solver": vote.solver_name, "baseline_only": True},
                    )
                )

            for left_label, right_label in combinations(target_group_labels, 2):
                key = tuple(sorted((left_label, right_label)))
                if key in compatibility_keys:
                    continue
                compatibility_keys.add(key)
                compatibility_records.append(
                    CrossGroupCompatibility(
                        left_group_label=left_label,
                        right_group_label=right_label,
                        compatibility_kind="alternative_solver_mix",
                        shared_signals=["ensemble_disagreement"],
                        risk_weight=0.25,
                        notes=[
                            "Groups co-occurred inside a baseline alternative grouping proposal.",
                        ],
                        metadata={"source_solver": vote.solver_name, "baseline_only": True},
                    )
                )

    alternative_count = len(alternative_groupings)
    leakage_count = len(leakage_records)
    penalty_hint = round(min(1.0, (alternative_count * 0.25) + (leakage_count * 0.05)), 3)

    if penalty_hint >= 0.7:
        risk_level = AmbiguityRiskLevel.CRITICAL
    elif penalty_hint >= 0.45:
        risk_level = AmbiguityRiskLevel.HIGH
    elif penalty_hint > 0.0:
        risk_level = AmbiguityRiskLevel.MEDIUM
    else:
        risk_level = AmbiguityRiskLevel.LOW

    triggered_flags: list[str] = []
    if alternative_count:
        triggered_flags.append("alternative_groupings_detected")
    if leakage_count:
        triggered_flags.append("word_group_leakage_detected")
    if compatibility_records:
        triggered_flags.append("cross_group_compatibility_detected")

    return AmbiguityReport(
        evaluator_name="baseline_ambiguity_evaluator",
        risk_level=risk_level,
        penalty_hint=penalty_hint,
        reject_recommended=penalty_hint >= 0.5,
        summary=(
            "Baseline ambiguity scaffold converted ensemble disagreement into placeholder "
            "leakage and alternative-grouping evidence."
        ),
        evidence=AmbiguityEvidence(
            word_group_leakage=leakage_records,
            cross_group_compatibility=compatibility_records,
            alternative_groupings=alternative_groupings,
            triggered_flags=triggered_flags,
            notes=[
                "Evidence originates from baseline solver disagreement rather than final ambiguity logic.",
            ],
        ),
        notes=[
            "Penalty and risk mapping are provisional scaffold values only.",
            "TODO[HUMAN_CORE]: replace with real ambiguity reasoning and threshold policy.",
        ],
        metadata={"baseline_only": True},
    )
