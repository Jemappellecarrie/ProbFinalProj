"""Human-owned ambiguity and leakage evaluation strategy.

File location:
    backend/app/solver/human_ambiguity_strategy.py

Purpose:
    Evaluate whether a composed puzzle permits alternative valid groupings or
    leaks enough signal across groups to feel unfair or unlike the target style.

Implementation:
    Uses cosine similarity between word embeddings (from context.run_metadata)
    to detect cross-group leakage. High cross-group similarity suggests a word
    could plausibly belong to multiple groups, which is the core ambiguity risk.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

from app.core.enums import RejectReasonCode
from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import (
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    EnsembleSolverResult,
    WordGroupLeakage,
)
from app.schemas.puzzle_models import PuzzleCandidate, RejectReason, SolverResult, VerificationResult
from app.solver.base import BaseAmbiguityEvaluator

LEAKAGE_THRESHOLD = 0.65


class HumanAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Embedding-based cross-group leakage evaluator."""

    evaluator_name = "human_ambiguity_evaluator"

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
        ensemble_result: EnsembleSolverResult | None = None,
    ) -> VerificationResult:
        features_by_word_id = context.run_metadata.get("features_by_word_id", {})

        leakage_records: list[WordGroupLeakage] = []
        max_cross_sim = 0.0

        if features_by_word_id:
            for group_a, group_b in combinations(puzzle.groups, 2):
                for wid_a in group_a.word_ids:
                    feat_a = features_by_word_id.get(wid_a)
                    if feat_a is None or "embedding" not in feat_a.debug_attributes:
                        continue
                    vec_a = np.array(feat_a.debug_attributes["embedding"], dtype=np.float32)
                    vec_a = vec_a / max(float(np.linalg.norm(vec_a)), 1e-9)

                    for wid_b in group_b.word_ids:
                        feat_b = features_by_word_id.get(wid_b)
                        if feat_b is None or "embedding" not in feat_b.debug_attributes:
                            continue
                        vec_b = np.array(feat_b.debug_attributes["embedding"], dtype=np.float32)
                        vec_b = vec_b / max(float(np.linalg.norm(vec_b)), 1e-9)

                        sim = float(vec_a @ vec_b)
                        if sim > max_cross_sim:
                            max_cross_sim = sim

                        if sim > LEAKAGE_THRESHOLD:
                            leakage_records.append(
                                WordGroupLeakage(
                                    word=feat_a.normalized,
                                    word_id=wid_a,
                                    source_group_label=group_a.label,
                                    target_group_label=group_b.label,
                                    leakage_kind="embedding_cosine_similarity",
                                    evidence_strength=round(sim, 4),
                                    notes=[
                                        f"Cosine similarity {sim:.4f} exceeds leakage threshold "
                                        f"{LEAKAGE_THRESHOLD}."
                                    ],
                                )
                            )

        leakage_estimate = min(1.0, len(leakage_records) * 0.1 + max_cross_sim * 0.3)
        alternative_count = solver_result.alternative_groupings_detected
        ambiguity_score = min(
            1.0, 0.4 * leakage_estimate + 0.6 * alternative_count * 0.2
        )

        if ambiguity_score >= 0.7:
            risk_level = AmbiguityRiskLevel.CRITICAL
        elif ambiguity_score >= 0.45:
            risk_level = AmbiguityRiskLevel.HIGH
        elif ambiguity_score > 0.0:
            risk_level = AmbiguityRiskLevel.MEDIUM
        else:
            risk_level = AmbiguityRiskLevel.LOW

        reject_recommended = risk_level in {AmbiguityRiskLevel.CRITICAL, AmbiguityRiskLevel.HIGH}

        triggered_flags: list[str] = []
        if leakage_records:
            triggered_flags.append("embedding_leakage_detected")
        if alternative_count:
            triggered_flags.append("alternative_groupings_detected")

        report = AmbiguityReport(
            evaluator_name=self.evaluator_name,
            risk_level=risk_level,
            penalty_hint=round(ambiguity_score, 4),
            reject_recommended=reject_recommended,
            summary=(
                f"Embedding-based leakage check: {len(leakage_records)} cross-group word pairs "
                f"exceed similarity threshold {LEAKAGE_THRESHOLD}. "
                f"Max cross-group cosine sim: {max_cross_sim:.4f}."
            ),
            evidence=AmbiguityEvidence(
                word_group_leakage=leakage_records,
                triggered_flags=triggered_flags,
                notes=[
                    "Leakage detected via cosine similarity of sentence-transformer embeddings.",
                ],
            ),
            notes=[
                f"leakage_estimate={leakage_estimate:.4f}, "
                f"ambiguity_score={ambiguity_score:.4f}, "
                f"risk_level={risk_level.value}",
            ],
        )

        reject_reasons: list[RejectReason] = []
        if reject_recommended:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.AMBIGUOUS_GROUPING,
                    message=(
                        f"Ambiguity evaluator flagged puzzle at risk level {risk_level.value}."
                    ),
                    metadata={
                        "risk_level": risk_level.value,
                        "leakage_count": len(leakage_records),
                        "max_cross_sim": round(max_cross_sim, 4),
                    },
                )
            )

        return VerificationResult(
            passed=not reject_recommended,
            reject_reasons=reject_reasons,
            leakage_estimate=round(leakage_estimate, 4),
            ambiguity_score=round(ambiguity_score, 4),
            ambiguity_report=report,
            ensemble_result=ensemble_result,
            notes=[
                "Human ambiguity evaluation uses embedding cosine similarity for leakage detection.",
            ],
        )
