"""Stage 1 ambiguity analysis for mixed-mechanism boards.

This module implements the repository's first real ambiguity-policy layer for
semantic, lexical, and theme boards. The output is evidence-rich and deterministic, but it is
still intentionally framed as Stage 1 machine policy rather than final
editorial truth.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from statistics import mean

from app.core.enums import RejectReasonCode, VerificationDecision
from app.core.stage1_quality import STAGE1_THRESHOLDS, clamp_unit
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import (
    cosine_similarity,
    mean_pairwise_similarity,
    normalize_signal,
    signal_label,
    vector_centroid,
)
from app.schemas.evaluation_models import (
    AlternativeGroupingCandidate,
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    BoardAmbiguitySummary,
    CrossGroupCompatibility,
    EnsembleSolverResult,
    GroupCoherenceSummary,
    WordFitSummary,
    WordGroupLeakage,
)
from app.schemas.puzzle_models import (
    GroupCandidate,
    PuzzleCandidate,
    RejectReason,
    SolverResult,
    VerificationResult,
)
from app.solver.base import BaseAmbiguityEvaluator
from app.utils.ids import stable_id


def _word_vector(word_id: str, context: GenerationContext) -> list[float]:
    features_by_word_id = context.run_metadata.get("features_by_word_id", {})
    feature = features_by_word_id.get(word_id)
    if feature is None:
        return []
    raw = feature.debug_attributes.get("semantic_sketch", [])
    return [float(value) for value in raw] if isinstance(raw, list) else []


def _word_signals(word_id: str, context: GenerationContext) -> set[str]:
    features_by_word_id = context.run_metadata.get("features_by_word_id", {})
    feature = features_by_word_id.get(word_id)
    if feature is None:
        return set()
    return (
        set(feature.semantic_tags)
        | set(feature.theme_tags)
        | set(feature.lexical_signals)
        | set(feature.phonetic_signals)
    )


def _group_signals(group: GroupCandidate) -> set[str]:
    evidence = group.metadata.get("evidence", {})
    explicit = set(group.metadata.get("shared_tags", [])) | set(evidence.get("shared_signals", []))
    normalized_label = normalize_signal(
        group.metadata.get("normalized_label", normalize_signal(group.label))
    )
    label_tokens = {token for token in normalized_label.split("_") if token}
    return explicit | label_tokens


def _group_centroid(
    group: GroupCandidate,
    context: GenerationContext,
    *,
    exclude_word_id: str | None = None,
) -> list[float]:
    if exclude_word_id is None and group.metadata.get("semantic_centroid"):
        raw = group.metadata.get("semantic_centroid", [])
        return [float(value) for value in raw] if isinstance(raw, list) else []

    vectors = [
        _word_vector(word_id, context)
        for word_id in group.word_ids
        if word_id != exclude_word_id and _word_vector(word_id, context)
    ]
    return vector_centroid(vectors) if vectors else []


def _signal_overlap(word_signals: set[str], group_signals: set[str]) -> float:
    if not word_signals or not group_signals:
        return 0.0
    return len(word_signals & group_signals) / len(group_signals)


def _word_to_group_fit(
    word_id: str,
    group: GroupCandidate,
    context: GenerationContext,
    *,
    exclude_word_id: str | None = None,
) -> tuple[float, float, float]:
    vector_score = cosine_similarity(
        _word_vector(word_id, context),
        _group_centroid(group, context, exclude_word_id=exclude_word_id),
    )
    signal_score = _signal_overlap(_word_signals(word_id, context), _group_signals(group))
    support = clamp_unit((0.8 * vector_score) + (0.2 * signal_score))
    return support, vector_score, signal_score


def _pairwise_signal_overlap(signal_sets: list[set[str]]) -> float:
    if len(signal_sets) < 2:
        return 0.0

    overlaps: list[float] = []
    for left_index, right_index in combinations(range(len(signal_sets)), 2):
        left = signal_sets[left_index]
        right = signal_sets[right_index]
        union = left | right
        if not union:
            overlaps.append(0.0)
            continue
        overlaps.append(len(left & right) / len(union))
    return mean(overlaps) if overlaps else 0.0


def _severity_for_word(competing_fit: float, margin: float) -> str:
    if (
        competing_fit >= STAGE1_THRESHOLDS.word_leakage_high_fit
        and margin <= STAGE1_THRESHOLDS.word_leakage_high_margin
    ):
        return "high"
    if (
        competing_fit >= STAGE1_THRESHOLDS.word_leakage_medium_fit
        and margin <= STAGE1_THRESHOLDS.word_leakage_medium_margin
    ):
        return "medium"
    return "low"


def _risk_level_from_summary(
    board_pressure: float,
    max_alternative_group_pressure: float,
    max_cross_group_pressure: float,
    high_leakage_word_count: int,
) -> AmbiguityRiskLevel:
    if (
        board_pressure >= STAGE1_THRESHOLDS.board_pressure_reject
        or max_alternative_group_pressure >= STAGE1_THRESHOLDS.alternative_group_reject
        or max_cross_group_pressure >= STAGE1_THRESHOLDS.cross_group_reject
        or high_leakage_word_count >= STAGE1_THRESHOLDS.high_leakage_word_reject
    ):
        return AmbiguityRiskLevel.CRITICAL
    if (
        board_pressure >= STAGE1_THRESHOLDS.board_pressure_borderline
        or max_alternative_group_pressure >= STAGE1_THRESHOLDS.alternative_group_borderline
        or max_cross_group_pressure >= STAGE1_THRESHOLDS.cross_group_borderline
    ):
        return AmbiguityRiskLevel.HIGH
    if board_pressure > 0.15 or max_cross_group_pressure > 0.3:
        return AmbiguityRiskLevel.MEDIUM
    return AmbiguityRiskLevel.LOW


def _decision_from_summary(
    board_summary: BoardAmbiguitySummary,
    weakest_group_support: float,
) -> VerificationDecision:
    if (
        board_summary.board_pressure >= STAGE1_THRESHOLDS.board_pressure_reject
        or board_summary.max_alternative_group_pressure
        >= STAGE1_THRESHOLDS.alternative_group_reject
        or board_summary.metrics.get("max_cross_group_pressure", 0.0)
        >= STAGE1_THRESHOLDS.cross_group_reject
        or board_summary.high_leakage_word_count >= STAGE1_THRESHOLDS.high_leakage_word_reject
        or weakest_group_support < STAGE1_THRESHOLDS.weak_group_support_reject
    ):
        return VerificationDecision.REJECT

    if (
        board_summary.board_pressure >= STAGE1_THRESHOLDS.board_pressure_borderline
        or board_summary.max_alternative_group_pressure
        >= STAGE1_THRESHOLDS.alternative_group_borderline
        or board_summary.metrics.get("max_cross_group_pressure", 0.0)
        >= STAGE1_THRESHOLDS.cross_group_borderline
        or weakest_group_support < STAGE1_THRESHOLDS.weak_group_support_borderline
    ):
        return VerificationDecision.BORDERLINE

    return VerificationDecision.ACCEPT


class ExperimentalSemanticAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Compatibility alias for the Stage 1 ambiguity evaluator."""

    evaluator_name = "experimental_semantic_ambiguity_evaluator"

    def _best_competing_group(
        self,
        word_id: str,
        assigned_group: GroupCandidate,
        puzzle: PuzzleCandidate,
        context: GenerationContext,
    ) -> tuple[GroupCandidate | None, float]:
        competing: list[tuple[GroupCandidate, float]] = []
        for group in puzzle.groups:
            if group.label == assigned_group.label:
                continue
            fit, _, _ = _word_to_group_fit(word_id, group, context)
            competing.append((group, fit))
        if not competing:
            return None, 0.0
        return max(competing, key=lambda item: (item[1], item[0].label))

    def _strongest_target_word(
        self,
        word_id: str,
        group: GroupCandidate,
        context: GenerationContext,
    ) -> tuple[str | None, str | None, float]:
        word_vector = _word_vector(word_id, context)
        best_word: tuple[str | None, str | None, float] = (None, None, 0.0)
        for target_word, target_word_id in zip(group.words, group.word_ids, strict=True):
            similarity = cosine_similarity(word_vector, _word_vector(target_word_id, context))
            candidate = (target_word, target_word_id, similarity)
            if candidate[2] > best_word[2]:
                best_word = candidate
        return best_word

    def _group_coherence_and_leakage(
        self,
        puzzle: PuzzleCandidate,
        context: GenerationContext,
    ) -> tuple[list[GroupCoherenceSummary], list[WordFitSummary], list[WordGroupLeakage]]:
        group_summaries: list[GroupCoherenceSummary] = []
        word_summaries: list[WordFitSummary] = []
        leakage_records: list[WordGroupLeakage] = []

        for group in puzzle.groups:
            assigned_supports: list[float] = []
            competing_supports: list[float] = []

            for word, word_id in zip(group.words, group.word_ids, strict=True):
                assigned_support, vector_score, signal_score = _word_to_group_fit(
                    word_id,
                    group,
                    context,
                    exclude_word_id=word_id,
                )
                competing_group, strongest_competing_support = self._best_competing_group(
                    word_id,
                    group,
                    puzzle,
                    context,
                )
                leakage_margin = round(assigned_support - strongest_competing_support, 4)
                severity = _severity_for_word(strongest_competing_support, leakage_margin)

                assigned_supports.append(assigned_support)
                competing_supports.append(strongest_competing_support)
                word_summaries.append(
                    WordFitSummary(
                        word=word,
                        word_id=word_id,
                        assigned_group_label=group.label,
                        assigned_support=round(assigned_support, 4),
                        strongest_competing_group_label=(
                            competing_group.label if competing_group is not None else None
                        ),
                        strongest_competing_support=round(strongest_competing_support, 4),
                        leakage_margin=leakage_margin,
                        severity=severity,
                        notes=[
                            (
                                "Assigned support uses leave-one-out group fit so the word is "
                                "judged against the other three members."
                            )
                        ],
                        metadata={
                            "vector_score": round(vector_score, 4),
                            "signal_score": round(signal_score, 4),
                        },
                    )
                )

                if severity == "low" or competing_group is None:
                    continue
                target_word, target_word_id, target_similarity = self._strongest_target_word(
                    word_id,
                    competing_group,
                    context,
                )
                leakage_records.append(
                    WordGroupLeakage(
                        word=word,
                        word_id=word_id,
                        source_group_label=group.label,
                        target_group_label=competing_group.label,
                        leakage_kind="stage1_best_competing_group_fit",
                        evidence_strength=round(strongest_competing_support, 4),
                        notes=[
                            (
                                "Word has meaningful support in another true group under the "
                                "Stage 1 fit heuristic."
                            )
                        ],
                        metadata={
                            "assigned_support": round(assigned_support, 4),
                            "leakage_margin": leakage_margin,
                            "severity": severity,
                            "target_word": target_word,
                            "target_word_id": target_word_id,
                            "target_similarity": round(target_similarity, 4),
                        },
                    )
                )

            group_summaries.append(
                GroupCoherenceSummary(
                    group_label=group.label,
                    support_score=round(mean(assigned_supports), 4) if assigned_supports else 0.0,
                    mean_pairwise_similarity=round(
                        float(group.metadata.get("mean_pairwise_similarity", 0.0)),
                        4,
                    ),
                    weakest_member_support=round(min(assigned_supports), 4)
                    if assigned_supports
                    else 0.0,
                    strongest_competing_fit=round(max(competing_supports), 4)
                    if competing_supports
                    else 0.0,
                    notes=[],
                    metadata={
                        "confidence": float(group.confidence),
                        "shared_signals": sorted(_group_signals(group)),
                    },
                )
            )

        return group_summaries, word_summaries, leakage_records

    def _cross_group_pressure(
        self,
        puzzle: PuzzleCandidate,
        context: GenerationContext,
    ) -> list[CrossGroupCompatibility]:
        compatibilities: list[CrossGroupCompatibility] = []

        for left_group, right_group in combinations(puzzle.groups, 2):
            left_to_right = [
                _word_to_group_fit(word_id, right_group, context)[0]
                for word_id in left_group.word_ids
            ]
            right_to_left = [
                _word_to_group_fit(word_id, left_group, context)[0]
                for word_id in right_group.word_ids
            ]
            max_cross_fit = (
                max(left_to_right + right_to_left) if left_to_right or right_to_left else 0.0
            )
            mean_cross_fit = (
                mean(left_to_right + right_to_left) if left_to_right or right_to_left else 0.0
            )
            pair_pressure = clamp_unit((0.6 * mean_cross_fit) + (0.4 * max_cross_fit))
            shared_signals = sorted(_group_signals(left_group) & _group_signals(right_group))

            compatibilities.append(
                CrossGroupCompatibility(
                    left_group_label=left_group.label,
                    right_group_label=right_group.label,
                    compatibility_kind="semantic_cross_group_leakage",
                    shared_signals=shared_signals,
                    risk_weight=round(pair_pressure, 4),
                    notes=["Risk weight summarizes how strongly each group's words fit the other."],
                    metadata={
                        "mean_left_to_right": round(mean(left_to_right), 4),
                        "mean_right_to_left": round(mean(right_to_left), 4),
                        "max_cross_fit": round(max_cross_fit, 4),
                    },
                )
            )

        return sorted(
            compatibilities,
            key=lambda record: (
                -record.risk_weight,
                record.left_group_label,
                record.right_group_label,
            ),
        )

    def _alternative_groups(
        self,
        puzzle: PuzzleCandidate,
        context: GenerationContext,
    ) -> list[AlternativeGroupingCandidate]:
        word_records = [
            {
                "word": word,
                "word_id": word_id,
                "group_label": group.label,
                "vector": _word_vector(word_id, context),
                "signals": _word_signals(word_id, context),
            }
            for group in puzzle.groups
            for word, word_id in zip(group.words, group.word_ids, strict=True)
        ]
        true_group_sets = {frozenset(group.word_ids) for group in puzzle.groups}
        candidates: list[AlternativeGroupingCandidate] = []

        for combination_records in combinations(word_records, 4):
            word_ids = [record["word_id"] for record in combination_records]
            if frozenset(word_ids) in true_group_sets:
                continue

            source_group_counts = Counter(record["group_label"] for record in combination_records)
            source_group_count = len(source_group_counts)
            if source_group_count < 2:
                continue

            vectors = [record["vector"] for record in combination_records if record["vector"]]
            signal_sets = [record["signals"] for record in combination_records]
            shared_signals = sorted(set.intersection(*signal_sets)) if signal_sets else []
            vector_coherence = mean_pairwise_similarity(vectors)
            pairwise_signal_overlap = _pairwise_signal_overlap(signal_sets)
            shared_signal_score = 1.0 if shared_signals else pairwise_signal_overlap
            balance_score = 1.0 - (max(source_group_counts.values()) / 4.0)
            distinct_group_score = (source_group_count - 1) / 3.0
            dominance_penalty = 0.15 if max(source_group_counts.values()) >= 3 else 0.0
            suspicion_score = clamp_unit(
                (0.45 * vector_coherence)
                + (0.25 * shared_signal_score)
                + (0.15 * balance_score)
                + (0.15 * distinct_group_score)
                - dominance_penalty
            )
            if suspicion_score < STAGE1_THRESHOLDS.alternative_group_borderline:
                continue

            words = [record["word"] for record in combination_records]
            candidates.append(
                AlternativeGroupingCandidate(
                    candidate_id=stable_id("alt_group", puzzle.puzzle_id, tuple(sorted(word_ids))),
                    source_solver=self.evaluator_name,
                    words=words,
                    word_ids=word_ids,
                    proposed_groups=[words],
                    matched_target_solution=False,
                    overlap_ratio=round(max(source_group_counts.values()) / 4.0, 4),
                    label_hint=signal_label(shared_signals[0]) if shared_signals else None,
                    coherence_score=round(vector_coherence, 4),
                    shared_signal_score=round(shared_signal_score, 4),
                    source_group_count=source_group_count,
                    suspicion_score=round(suspicion_score, 4),
                    notes=[
                        (
                            "Enumerated from the board's 4-word subsets as "
                            "a suspicious mixed-source group."
                        )
                    ],
                    metadata={
                        "shared_signals": shared_signals,
                        "source_groups": dict(sorted(source_group_counts.items())),
                        "pairwise_signal_overlap": round(pairwise_signal_overlap, 4),
                        "balance_score": round(balance_score, 4),
                        "dominance_penalty": round(dominance_penalty, 4),
                    },
                )
            )

        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.suspicion_score,
                -candidate.source_group_count,
                tuple(candidate.words),
            ),
        )
        return ranked[: STAGE1_THRESHOLDS.alternative_group_limit]

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
        ensemble_result: EnsembleSolverResult | None = None,
    ) -> VerificationResult:
        group_summaries, word_summaries, leakage_records = self._group_coherence_and_leakage(
            puzzle,
            context,
        )
        compatibilities = self._cross_group_pressure(puzzle, context)
        alternatives = self._alternative_groups(puzzle, context)

        high_leakage_word_count = sum(1 for summary in word_summaries if summary.severity == "high")
        medium_leakage_word_count = sum(
            1 for summary in word_summaries if summary.severity in {"medium", "high"}
        )
        max_alt_pressure = max(
            (candidate.suspicion_score for candidate in alternatives),
            default=0.0,
        )
        max_cross_group_pressure = max(
            (record.risk_weight for record in compatibilities),
            default=0.0,
        )
        max_competing_fit = max(
            (summary.strongest_competing_support for summary in word_summaries),
            default=0.0,
        )
        weakest_group_support = min(
            (summary.support_score for summary in group_summaries),
            default=0.0,
        )
        board_pressure = clamp_unit(
            (0.35 * max_alt_pressure)
            + (0.3 * max_cross_group_pressure)
            + (0.2 * max_competing_fit)
            + (0.15 * (1.0 - weakest_group_support))
        )
        strongest_confusing_pair = compatibilities[0] if compatibilities else None

        warning_flags: list[str] = []
        if max_alt_pressure >= STAGE1_THRESHOLDS.alternative_group_borderline:
            warning_flags.append("strong_alternative_group")
        if max_cross_group_pressure >= STAGE1_THRESHOLDS.cross_group_borderline:
            warning_flags.append("cross_group_semantic_similarity")
        if high_leakage_word_count > 0:
            warning_flags.append("high_word_leakage")
        elif medium_leakage_word_count >= STAGE1_THRESHOLDS.high_leakage_word_borderline:
            warning_flags.append("moderate_word_leakage")
        if weakest_group_support < STAGE1_THRESHOLDS.weak_group_support_borderline:
            warning_flags.append("weak_group_support")
        if solver_result.alternative_groupings_detected > 0:
            warning_flags.append("solver_alternative_groupings_detected")

        risk_level = _risk_level_from_summary(
            board_pressure,
            max_alt_pressure,
            max_cross_group_pressure,
            high_leakage_word_count,
        )
        board_summary = BoardAmbiguitySummary(
            board_pressure=round(board_pressure, 4),
            max_alternative_group_pressure=round(max_alt_pressure, 4),
            high_leakage_word_count=high_leakage_word_count,
            strongest_confusing_pair=(
                (
                    f"{strongest_confusing_pair.left_group_label} <-> "
                    f"{strongest_confusing_pair.right_group_label}"
                )
                if strongest_confusing_pair is not None
                else None
            ),
            severity=risk_level.value,
            warning_flags=sorted(set(warning_flags)),
            metrics={
                "max_cross_group_pressure": round(max_cross_group_pressure, 4),
                "max_competing_fit": round(max_competing_fit, 4),
                "medium_or_high_leakage_word_count": float(medium_leakage_word_count),
                "weakest_group_support": round(weakest_group_support, 4),
            },
        )
        decision = _decision_from_summary(board_summary, weakest_group_support)

        evidence_refs = ["board_summary"]
        if strongest_confusing_pair is not None:
            evidence_refs.append(
                "pair:"
                f"{strongest_confusing_pair.left_group_label}__"
                f"{strongest_confusing_pair.right_group_label}"
            )
        if alternatives:
            evidence_refs.append(f"alternative:{'|'.join(alternatives[0].words)}")
        weak_groups = [
            summary.group_label
            for summary in group_summaries
            if summary.support_score < STAGE1_THRESHOLDS.weak_group_support_borderline
        ]
        evidence_refs.extend(f"group:{label}" for label in weak_groups)

        ambiguity_report = AmbiguityReport(
            evaluator_name=self.evaluator_name,
            risk_level=risk_level,
            penalty_hint=round(board_pressure, 4),
            reject_recommended=decision is VerificationDecision.REJECT,
            summary=(
                "Stage 1 ambiguity analysis computed per-word leakage, cross-group "
                "pressure, and suspicious alternative 4-word groups from the board."
            ),
            evidence=AmbiguityEvidence(
                group_coherence_summaries=group_summaries,
                word_fit_summaries=word_summaries,
                word_group_leakage=leakage_records,
                cross_group_compatibility=compatibilities,
                alternative_groupings=alternatives,
                board_summary=board_summary,
                triggered_flags=sorted(set(warning_flags)),
                notes=[
                    (
                        "Scores are Stage 1 heuristics derived from semantic-sketch fit, "
                        "shared signals, and exhaustive board subset search."
                    ),
                ],
            ),
            notes=[
                "Stage 1 ambiguity policy is implemented and testable.",
                "Final editorial ambiguity judgment remains outside the scope of this layer.",
            ],
            metadata={
                "solver_backend": solver_result.backend_name,
                "solver_alternative_groupings_detected": (
                    solver_result.alternative_groupings_detected
                ),
            },
        )

        reject_reasons: list[RejectReason] = []
        if decision is VerificationDecision.REJECT:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.AMBIGUOUS_GROUPING,
                    message=(
                        "Stage 1 ambiguity policy rejected the puzzle due to strong leakage "
                        "pressure or a highly plausible alternative group."
                    ),
                    metadata={
                        "board_pressure": round(board_pressure, 4),
                        "max_alternative_group_pressure": round(max_alt_pressure, 4),
                        "max_cross_group_pressure": round(max_cross_group_pressure, 4),
                        "high_leakage_word_count": high_leakage_word_count,
                    },
                )
            )

        return VerificationResult(
            passed=decision is not VerificationDecision.REJECT,
            decision=decision,
            reject_reasons=reject_reasons,
            warning_flags=board_summary.warning_flags,
            leakage_estimate=round(max_cross_group_pressure, 4),
            ambiguity_score=round(board_pressure, 4),
            summary_metrics={
                "board_pressure": round(board_pressure, 4),
                "max_alternative_group_pressure": round(max_alt_pressure, 4),
                "max_cross_group_pressure": round(max_cross_group_pressure, 4),
                "high_leakage_word_count": float(high_leakage_word_count),
                "weakest_group_support": round(weakest_group_support, 4),
            },
            evidence_refs=evidence_refs,
            ambiguity_report=ambiguity_report,
            ensemble_result=ensemble_result,
            notes=[
                (
                    "Stage 1 ambiguity evaluation uses board-intrinsic evidence "
                    "rather than solver-only disagreement."
                )
            ],
            metadata={"stage": "stage1_quality_control"},
        )


class HumanAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Public Stage 1 ambiguity evaluator used by the non-demo pipeline."""

    evaluator_name = "human_ambiguity_evaluator"

    def __init__(self) -> None:
        self._delegate = ExperimentalSemanticAmbiguityEvaluator()

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
        ensemble_result: EnsembleSolverResult | None = None,
    ) -> VerificationResult:
        result = self._delegate.evaluate(
            puzzle,
            solver_result,
            context,
            ensemble_result=ensemble_result,
        )
        if result.ambiguity_report is not None:
            result.ambiguity_report.evaluator_name = self.evaluator_name
        result.notes.append("HumanAmbiguityEvaluator exposes the Stage 1 board-analysis policy.")
        return result
