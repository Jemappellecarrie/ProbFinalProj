"""Final quality acceptance batch service."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config.settings import Settings
from app.core.editorial_quality import (
    empty_run_family_accounting,
    ensure_run_family_accounting,
    record_editorial_family_signature,
    record_label_family_signature,
    record_mechanism_template_signature,
    record_semantic_majority_board,
    record_surface_wordplay_family_signatures,
    record_theme_family_signatures,
)
from app.core.policy_snapshot import current_policy_snapshot
from app.core.stage1_quality import verification_decision_rank
from app.core.stage3_style_policy import STAGE3_EDITORIAL_SELECTION_POLICY
from app.schemas.api import PuzzleGenerationRequest
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    BatchEvaluationSummary,
    CandidatePoolPuzzleRecord,
    FinalQualityBatchConfig,
    RankedPuzzleRecord,
    RejectedPuzzleRecord,
    TopKSummary,
)
from app.scoring.calibration import (
    build_batch_calibration_summary,
    build_calibration_artifact_payloads,
)
from app.scoring.funnel_report import board_signature, build_funnel_report, funnel_report_markdown
from app.services.evaluation_service import EvaluationService
from app.services.generation_service import GenerationService


@dataclass(slots=True)
class FinalQualityBatchRun:
    """Persisted final-quality batch output."""

    config: FinalQualityBatchConfig
    summary: BatchEvaluationSummary
    candidate_records: list[CandidatePoolPuzzleRecord]
    request_diagnostics: list[dict[str, object]]
    output_files: dict[str, str]


class FinalQualityAcceptanceService:
    """Run the acceptance-sprint batch with candidate-pool persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._generation_service = GenerationService(settings)
        self._evaluation_service = EvaluationService(settings)

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    @staticmethod
    def _score_sort_key(
        record: CandidatePoolPuzzleRecord,
    ) -> tuple[float, ...]:
        style_metrics = (
            record.style_analysis.board_style_summary.metrics
            if record.style_analysis is not None
            and record.style_analysis.board_style_summary is not None
            else {}
        )
        semantic_majority_preference = 1 if record_semantic_majority_board(record) else 0
        return (
            -verification_decision_rank(record.verification_decision),
            -semantic_majority_preference,
            -float(style_metrics.get("semantic_group_count", 0.0)),
            float(style_metrics.get("low_payoff_pattern_flags", 0.0)),
            float(style_metrics.get("microtheme_smallness", 0.0)),
            float(style_metrics.get("formulaic_mix_score", 0.0)),
            float(style_metrics.get("surface_wordplay_penalty_applied", 0.0)),
            float(style_metrics.get("surface_wordplay_score", 0.0)),
            -float(style_metrics.get("clue_payoff_bonus_applied", 0.0)),
            -float(style_metrics.get("phrase_payoff_score", 0.0)),
            -float(style_metrics.get("label_naturalness_score", 0.0)),
            -float(style_metrics.get("editorial_payoff_score", 0.0)),
            -record.score_breakdown.overall,
            record.score_breakdown.ambiguity_penalty,
            -float(record.score_breakdown.components.get("composer_ranking_score", 0.0)),
            record.request_seed,
            record.request_rank,
            record.puzzle_id,
        )

    def _candidate_record(
        self,
        *,
        iteration_index: int,
        request_seed: int,
        request_rank: int,
        selected: bool,
        response,
        selected_components: dict[str, str | list[str]],
    ) -> CandidatePoolPuzzleRecord:
        mechanism_mix_summary = dict(
            sorted(
                response.puzzle.metadata.get(
                    "mechanism_mix_summary",
                    {},
                ).items()
            )
        )
        return CandidatePoolPuzzleRecord(
            iteration_index=iteration_index,
            request_seed=request_seed,
            request_rank=request_rank,
            selected=selected,
            puzzle_id=response.puzzle.puzzle_id,
            board_words=response.puzzle.board_words,
            group_labels=[group.label for group in response.puzzle.groups],
            group_word_sets=[list(group.words) for group in response.puzzle.groups],
            group_types=[group.group_type.value for group in response.puzzle.groups],
            mechanism_mix_summary=mechanism_mix_summary,
            mixed_board=bool(response.puzzle.metadata.get("mixed_board", False)),
            group_family_signatures=list(
                response.puzzle.metadata.get("group_family_signatures", [])
            ),
            board_family_signature=response.puzzle.metadata.get("board_family_signature"),
            editorial_family_signature=response.puzzle.metadata.get("editorial_family_signature"),
            theme_family_signatures=list(
                response.puzzle.metadata.get("theme_family_signatures", [])
            ),
            surface_wordplay_family_signatures=list(
                response.puzzle.metadata.get("surface_wordplay_family_signatures", [])
            ),
            editorial_flags=list(response.puzzle.metadata.get("editorial_flags", [])),
            verification_decision=response.verification.decision.value,
            score_breakdown=self._evaluation_service._score_breakdown(response),
            reject_reasons=[reason.code.value for reason in response.verification.reject_reasons],
            ambiguity_report=response.verification.ambiguity_report,
            ensemble_result=response.verification.ensemble_result,
            style_analysis=response.score.style_analysis,
            trace_id=response.trace.trace_id if response.trace is not None else None,
            warnings=response.warnings,
            selected_components=selected_components,
            notes=(
                [self._evaluation_service._acceptance_note(response.demo_mode)]
                if response.verification.passed
                else [self._evaluation_service._rejection_note(response.demo_mode)]
            ),
        )

    def _selected_records(
        self, candidate_records: list[CandidatePoolPuzzleRecord]
    ) -> tuple[list[AcceptedPuzzleRecord], list[RejectedPuzzleRecord]]:
        accepted: list[AcceptedPuzzleRecord] = []
        rejected: list[RejectedPuzzleRecord] = []
        for record in candidate_records:
            if not record.selected:
                continue
            base_payload = {
                "iteration_index": record.iteration_index,
                "request_seed": record.request_seed,
                "puzzle_id": record.puzzle_id,
                "board_words": record.board_words,
                "group_labels": record.group_labels,
                "group_word_sets": record.group_word_sets,
                "group_types": record.group_types,
                "mechanism_mix_summary": record.mechanism_mix_summary,
                "mixed_board": record.mixed_board,
                "group_family_signatures": record.group_family_signatures,
                "board_family_signature": record.board_family_signature,
                "editorial_family_signature": record.editorial_family_signature,
                "theme_family_signatures": record.theme_family_signatures,
                "surface_wordplay_family_signatures": record.surface_wordplay_family_signatures,
                "editorial_flags": record.editorial_flags,
                "verification_decision": record.verification_decision,
                "score_breakdown": record.score_breakdown,
                "ambiguity_report": record.ambiguity_report,
                "ensemble_result": record.ensemble_result,
                "style_analysis": record.style_analysis,
                "trace_id": record.trace_id,
                "warnings": record.warnings,
                "selected_components": record.selected_components,
                "notes": record.notes,
            }
            if record.verification_decision == "reject":
                rejected.append(
                    RejectedPuzzleRecord(**base_payload, reject_reasons=record.reject_reasons)
                )
            else:
                accepted.append(AcceptedPuzzleRecord(**base_payload))
        return accepted, rejected

    @staticmethod
    def _family_diversity_allowed(
        record: CandidatePoolPuzzleRecord,
        selected: list[CandidatePoolPuzzleRecord],
    ) -> bool:
        editorial_family_signature = record_editorial_family_signature(record)
        label_family_signature = record_label_family_signature(record)
        theme_family_signatures = set(record_theme_family_signatures(record))
        surface_wordplay_family_signatures = set(record_surface_wordplay_family_signatures(record))
        editorial_flags = set(record.editorial_flags or [])
        mechanism_template_signature = record_mechanism_template_signature(record)

        if (
            sum(record_label_family_signature(existing) == label_family_signature for existing in selected)
            >= 1
        ):
            return False

        if (
            sum(
                record_editorial_family_signature(existing) == editorial_family_signature
                for existing in selected
            )
            >= STAGE3_EDITORIAL_SELECTION_POLICY.top_k_editorial_family_cap
        ):
            return False

        if "microtheme_trivia_smallness" in editorial_flags:
            for signature in theme_family_signatures:
                if (
                    sum(
                        signature in set(record_theme_family_signatures(existing))
                        for existing in selected
                    )
                    >= STAGE3_EDITORIAL_SELECTION_POLICY.top_k_theme_family_cap
                ):
                    return False

        for signature in surface_wordplay_family_signatures:
            if (
                sum(
                    signature in set(record_surface_wordplay_family_signatures(existing))
                    for existing in selected
                )
                >= STAGE3_EDITORIAL_SELECTION_POLICY.top_k_surface_wordplay_family_cap
            ):
                return False

        if "balanced_mixed_board" in editorial_flags and (
            sum(
                record_mechanism_template_signature(existing) == mechanism_template_signature
                for existing in selected
            )
            >= STAGE3_EDITORIAL_SELECTION_POLICY.top_k_balanced_mixed_template_cap
        ):
            return False

        return True

    def _rank_top_review_candidates(
        self,
        candidate_records: list[CandidatePoolPuzzleRecord],
        *,
        top_k_size: int,
    ) -> tuple[TopKSummary, list[CandidatePoolPuzzleRecord]]:
        passed_records = [
            record for record in candidate_records if record.verification_decision != "reject"
        ]
        unique_records: list[CandidatePoolPuzzleRecord] = []
        seen_signatures: set[str] = set()
        deferred_records: list[CandidatePoolPuzzleRecord] = []
        for record in sorted(passed_records, key=self._score_sort_key):
            signature = board_signature(record)
            if signature in seen_signatures:
                continue
            if self._family_diversity_allowed(record, unique_records):
                seen_signatures.add(signature)
                unique_records.append(record)
                if len(unique_records) >= top_k_size:
                    break
                continue
            deferred_records.append(record)

        if len(unique_records) < top_k_size:
            for record in deferred_records:
                signature = board_signature(record)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                unique_records.append(record)
                if len(unique_records) >= top_k_size:
                    break

        ranked = [
            RankedPuzzleRecord(
                rank=index + 1,
                puzzle_id=record.puzzle_id,
                accepted=record.verification_decision != "reject",
                verification_decision=record.verification_decision,
                board_words=record.board_words,
                group_labels=record.group_labels,
                group_word_sets=record.group_word_sets,
                group_types=record.group_types,
                mechanism_mix_summary=record.mechanism_mix_summary,
                mixed_board=record.mixed_board,
                group_family_signatures=record.group_family_signatures,
                board_family_signature=record.board_family_signature,
                editorial_family_signature=record.editorial_family_signature,
                theme_family_signatures=record.theme_family_signatures,
                surface_wordplay_family_signatures=record.surface_wordplay_family_signatures,
                editorial_flags=record.editorial_flags,
                score_breakdown=record.score_breakdown,
                ambiguity_risk_level=(
                    record.ambiguity_report.risk_level
                    if record.ambiguity_report is not None
                    else None
                ),
                ambiguity_penalty_hint=(
                    record.ambiguity_report.penalty_hint
                    if record.ambiguity_report is not None
                    else 0.0
                ),
                solver_agreement_ratio=(
                    record.ensemble_result.agreement_summary.agreement_ratio
                    if record.ensemble_result is not None
                    else None
                ),
                solver_disagreement_flags=(
                    record.ensemble_result.agreement_summary.disagreement_flags
                    if record.ensemble_result is not None
                    else []
                ),
                style_archetype=(
                    record.style_analysis.archetype.label
                    if record.style_analysis is not None
                    else None
                ),
                nyt_likeness_placeholder=(
                    record.style_analysis.nyt_likeness.score
                    if record.style_analysis is not None
                    else None
                ),
                style_alignment_score=(
                    record.style_analysis.board_style_summary.style_alignment_score
                    if record.style_analysis is not None
                    and record.style_analysis.board_style_summary is not None
                    else None
                ),
                style_out_of_band_flags=(
                    record.style_analysis.out_of_band_flags
                    if record.style_analysis is not None
                    else []
                ),
                ranking_influence_notes=[
                    "Top review ranking is built from the persisted request-level candidate pool.",
                    "Board-level dedupe is supplemented with editorial family-diversity caps.",
                ],
                trace_id=record.trace_id,
                reject_risk_flags=(
                    record.ambiguity_report.evidence.triggered_flags
                    if record.ambiguity_report is not None
                    else []
                ),
                notes=[
                    (
                        "Deduped by board signature, then ranked by decision class, overall score, "
                        "editorial payoff, ambiguity penalty, and composer score."
                    )
                ],
            )
            for index, record in enumerate(unique_records)
        ]
        return (
            TopKSummary(
                requested_k=top_k_size,
                returned_count=len(ranked),
                ranked_puzzles=ranked,
                notes=[
                    "Final-quality top-k is drawn from the persisted candidate pool, "
                    "not only selected winners."
                ],
            ),
            unique_records,
        )

    def run_batch(self, config: FinalQualityBatchConfig) -> FinalQualityBatchRun:
        """Run the final-quality batch and persist deterministic artifacts."""

        if config.demo_mode != self._settings.demo_mode:
            raise RuntimeError("FinalQualityBatchConfig.demo_mode must match Settings.demo_mode.")

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        seeds = [config.base_seed + index for index in range(config.num_requests)]
        run_family_accounting = ensure_run_family_accounting(empty_run_family_accounting())

        candidate_records: list[CandidatePoolPuzzleRecord] = []
        request_diagnostics: list[dict[str, object]] = []

        for iteration_index, request_seed in enumerate(seeds):
            print(
                f"[final-quality] starting request {iteration_index + 1}/{len(seeds)} seed={request_seed}",
                file=sys.stderr,
                flush=True,
            )
            result = self._generation_service.run_generation(
                PuzzleGenerationRequest(
                    seed=request_seed,
                    include_trace=config.save_traces,
                    developer_mode=config.save_traces,
                ),
                run_metadata={
                    "editorial_run_state": run_family_accounting,
                    "run_iteration_index": iteration_index,
                    "run_seed_schedule": seeds,
                },
            )
            selected_components = {
                "feature_extractor": result.components.feature_extractor,
                "generators": result.components.generators,
                "composer": result.components.composer,
                "solver": result.components.solver,
                "solver_registry": result.components.solver_registry,
                "verifier": result.components.verifier,
                "scorer": result.components.scorer,
                "style_analyzer": result.components.style_analyzer or "not_configured",
            }
            request_diagnostics.append(
                {
                    "iteration_index": iteration_index,
                    "request_seed": request_seed,
                    **result.composition_diagnostics,
                }
            )
            print(
                (
                    f"[final-quality] finished request {iteration_index + 1}/{len(seeds)} "
                    f"seed={request_seed} candidates={len(result.candidate_results)} "
                    f"selected={sum(1 for candidate in result.candidate_results if candidate.selected)}"
                ),
                file=sys.stderr,
                flush=True,
            )
            for candidate in result.candidate_results[: config.candidate_pool_limit]:
                response = type(
                    "CandidateResponse",
                    (),
                    {
                        "puzzle": candidate.puzzle,
                        "verification": candidate.verification,
                        "score": candidate.score,
                        "trace": result.trace if candidate.selected else None,
                        "warnings": result.warnings,
                        "demo_mode": self._settings.demo_mode,
                    },
                )()
                candidate_records.append(
                    self._candidate_record(
                        iteration_index=iteration_index,
                        request_seed=request_seed,
                        request_rank=candidate.request_rank,
                        selected=candidate.selected,
                        response=response,
                        selected_components=selected_components,
                    )
                )

        selected_accepted, selected_rejected = self._selected_records(candidate_records)
        top_k, top_review_candidates = self._rank_top_review_candidates(
            candidate_records,
            top_k_size=config.top_k_size,
        )
        calibration_summary = build_batch_calibration_summary(
            accepted_records=selected_accepted,
            rejected_records=selected_rejected,
            top_k_records=[
                AcceptedPuzzleRecord(
                    iteration_index=record.iteration_index,
                    request_seed=record.request_seed,
                    puzzle_id=record.puzzle_id,
                    board_words=record.board_words,
                    group_labels=record.group_labels,
                    group_word_sets=record.group_word_sets,
                    group_types=record.group_types,
                    mechanism_mix_summary=record.mechanism_mix_summary,
                    mixed_board=record.mixed_board,
                    verification_decision=record.verification_decision,
                    score_breakdown=record.score_breakdown,
                    ambiguity_report=record.ambiguity_report,
                    ensemble_result=record.ensemble_result,
                    style_analysis=record.style_analysis,
                    trace_id=record.trace_id,
                    warnings=record.warnings,
                    selected_components=record.selected_components,
                    notes=record.notes,
                )
                for record in top_review_candidates
            ],
        )
        summary = self._evaluation_service._summary(
            "final_quality_acceptance",
            output_dir,
            selected_accepted,
            selected_rejected,
            top_k,
            calibration_summary,
        )
        calibration_payloads = build_calibration_artifact_payloads(calibration_summary)
        funnel_report = build_funnel_report(
            total_generation_requests=config.num_requests,
            candidate_records=candidate_records,
            top_review_candidates=top_review_candidates,
            request_diagnostics=request_diagnostics,
        )

        borderline_records = [
            record.model_dump(mode="json")
            for record in selected_accepted
            if record.verification_decision == "borderline"
        ]
        output_files = {
            "batch_config": str(output_dir / "batch_config.json"),
            "seed_manifest": str(output_dir / "seed_manifest.json"),
            "policy_snapshot": str(output_dir / "policy_snapshot.json"),
            "summary": str(output_dir / "summary.json"),
            "accepted": str(output_dir / "accepted.json"),
            "borderline": str(output_dir / "borderline.json"),
            "rejected": str(output_dir / "rejected.json"),
            "candidate_pool": str(output_dir / "candidate_pool.json"),
            "top_k": str(output_dir / "top_k.json"),
            "calibration_summary": str(output_dir / "calibration_summary.json"),
            "style_summary": str(output_dir / "style_summary.json"),
            "mechanism_mix_summary": str(output_dir / "mechanism_mix_summary.json"),
            "threshold_diagnostics": str(output_dir / "threshold_diagnostics.json"),
            "funnel_report": str(output_dir / "funnel_report.json"),
            "funnel_report_markdown": str(output_dir / "funnel_report.md"),
            "request_diagnostics": str(output_dir / "request_diagnostics.json"),
        }

        self._write_json(Path(output_files["batch_config"]), config.model_dump(mode="json"))
        self._write_json(
            Path(output_files["seed_manifest"]),
            {
                "base_seed": config.base_seed,
                "count": config.num_requests,
                "seeds": seeds,
            },
        )
        self._write_json(Path(output_files["policy_snapshot"]), current_policy_snapshot())
        self._write_json(Path(output_files["summary"]), summary.model_dump(mode="json"))
        self._write_json(
            Path(output_files["accepted"]),
            [record.model_dump(mode="json") for record in selected_accepted],
        )
        self._write_json(Path(output_files["borderline"]), borderline_records)
        self._write_json(
            Path(output_files["rejected"]),
            [record.model_dump(mode="json") for record in selected_rejected],
        )
        self._write_json(
            Path(output_files["candidate_pool"]),
            [record.model_dump(mode="json") for record in candidate_records],
        )
        self._write_json(Path(output_files["top_k"]), top_k.model_dump(mode="json"))
        self._write_json(
            Path(output_files["calibration_summary"]),
            calibration_payloads["calibration_summary"],
        )
        self._write_json(Path(output_files["style_summary"]), calibration_payloads["style_summary"])
        self._write_json(
            Path(output_files["mechanism_mix_summary"]),
            calibration_payloads["mechanism_mix_summary"],
        )
        self._write_json(
            Path(output_files["threshold_diagnostics"]),
            calibration_payloads["threshold_diagnostics"],
        )
        self._write_json(Path(output_files["request_diagnostics"]), request_diagnostics)
        self._write_json(Path(output_files["funnel_report"]), funnel_report)
        (output_dir / "funnel_report.md").write_text(
            funnel_report_markdown(funnel_report),
            encoding="utf-8",
        )

        return FinalQualityBatchRun(
            config=config,
            summary=summary,
            candidate_records=candidate_records,
            request_diagnostics=request_diagnostics,
            output_files=output_files,
        )
