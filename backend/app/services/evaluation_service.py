"""Offline batch evaluation service.

Role in pipeline:
    Run many generation attempts, persist accepted/rejected artifacts, and
    produce lightweight summaries for debugging and future evaluation work.

Inputs:
    - `BatchEvaluationConfig`

Outputs:
    - `BatchEvaluationRun`
    - persisted JSON artifacts under `data/processed/eval_runs`

Why core logic is intentionally deferred:
    Final evaluation rubric, human-likeness benchmarking, and statistical
    significance policy remain human-owned. This service focuses on stable
    scaffolding and reproducible artifact output.

Acceptance criteria:
    - One CLI command can run a batch evaluation.
    - Accepted/rejected/top-k outputs are easy to inspect.
    - Output format is explicit about baseline/mock limitations.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

from app.config.settings import Settings
from app.core.stage1_quality import STAGE1_TOP_K_POLICY, verification_decision_rank
from app.schemas.api import PuzzleGenerationRequest
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    BatchEvaluationConfig,
    BatchEvaluationRun,
    BatchEvaluationSummary,
    CalibrationSummary,
    DebugComparisonView,
    GeneratorMixSummary,
    RankedPuzzleRecord,
    RejectedPuzzleRecord,
    RejectReasonHistogram,
    ScoreBreakdownView,
    ScoreDistributionSummary,
    SolverAgreementStatistics,
    TopKSummary,
)
from app.scoring.calibration import (
    build_batch_calibration_summary,
    build_calibration_artifact_payloads,
)
from app.services.generation_service import GenerationService
from app.utils.ids import new_id


class EvaluationService:
    """Service for batch generation analysis and persisted debug summaries."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._generation_service = GenerationService(settings)

    @staticmethod
    def _score_breakdown(response) -> ScoreBreakdownView:
        return ScoreBreakdownView(
            overall=response.score.overall,
            coherence=response.score.coherence,
            ambiguity_penalty=response.score.ambiguity_penalty,
            human_likeness=response.score.human_likeness,
            components=response.score.components,
        )

    @staticmethod
    def _acceptance_note(demo_mode: bool) -> str:
        if demo_mode:
            return (
                "Accepted using demo-generation scaffolds plus baseline verification and scoring."
            )
        return (
            "Accepted using the Stage 3 mixed-generation path with the Stage 1 "
            "quality-control core and Stage 3 style-analysis baseline."
        )

    @staticmethod
    def _rejection_note(demo_mode: bool) -> str:
        if demo_mode:
            return "Rejected using demo-generation scaffolds and baseline ambiguity checks."
        return (
            "Rejected using the Stage 3 mixed-generation path with the Stage 1 "
            "quality-control core and Stage 3 style-analysis baseline."
        )

    def _accepted_record(
        self,
        response,
        iteration_index: int,
        request_seed: int,
    ) -> AcceptedPuzzleRecord:
        mechanism_mix_summary = dict(
            sorted(
                response.puzzle.metadata.get(
                    "mechanism_mix_summary",
                    Counter(group.group_type.value for group in response.puzzle.groups),
                ).items()
            )
        )
        return AcceptedPuzzleRecord(
            iteration_index=iteration_index,
            request_seed=request_seed,
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
            score_breakdown=self._score_breakdown(response),
            ambiguity_report=response.verification.ambiguity_report,
            ensemble_result=response.verification.ensemble_result,
            style_analysis=response.score.style_analysis,
            trace_id=response.trace.trace_id if response.trace is not None else None,
            warnings=response.warnings,
            selected_components=response.selected_components,
            notes=[self._acceptance_note(response.demo_mode)],
        )

    def _rejected_record(
        self,
        response,
        iteration_index: int,
        request_seed: int,
    ) -> RejectedPuzzleRecord:
        mechanism_mix_summary = dict(
            sorted(
                response.puzzle.metadata.get(
                    "mechanism_mix_summary",
                    Counter(group.group_type.value for group in response.puzzle.groups),
                ).items()
            )
        )
        return RejectedPuzzleRecord(
            iteration_index=iteration_index,
            request_seed=request_seed,
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
            score_breakdown=self._score_breakdown(response),
            reject_reasons=[reason.code.value for reason in response.verification.reject_reasons],
            ambiguity_report=response.verification.ambiguity_report,
            ensemble_result=response.verification.ensemble_result,
            style_analysis=response.score.style_analysis,
            trace_id=response.trace.trace_id if response.trace is not None else None,
            warnings=response.warnings,
            selected_components=response.selected_components,
            notes=[self._rejection_note(response.demo_mode)],
        )

    @staticmethod
    def _rank_top_k(accepted_records: list[AcceptedPuzzleRecord], top_k_size: int) -> TopKSummary:
        sorted_records = sorted(
            accepted_records,
            key=lambda record: (
                -verification_decision_rank(record.verification_decision),
                -record.score_breakdown.overall,
                record.score_breakdown.ambiguity_penalty,
                -float(record.score_breakdown.components.get("composer_ranking_score", 0.0)),
                record.puzzle_id,
            ),
        )
        unique_records: list[AcceptedPuzzleRecord] = []
        seen_puzzle_ids: set[str] = set()
        for record in sorted_records:
            if record.puzzle_id in seen_puzzle_ids:
                continue
            unique_records.append(record)
            seen_puzzle_ids.add(record.puzzle_id)
        ranked = [
            RankedPuzzleRecord(
                rank=index + 1,
                puzzle_id=record.puzzle_id,
                accepted=True,
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
                ranking_influence_notes=(
                    [
                        "Stage 3 style alignment bonus contributed to ranking."
                        if (
                            record.style_analysis is not None
                            and record.style_analysis.board_style_summary is not None
                            and record.style_analysis.board_style_summary.style_alignment_score
                            > 0.0
                        )
                        else "No Stage 3 style alignment bonus was available."
                    ]
                ),
                trace_id=record.trace_id,
                reject_risk_flags=(
                    record.ambiguity_report.evidence.triggered_flags
                    if record.ambiguity_report is not None
                    else []
                ),
                notes=[
                    (
                        "Ranked by the Stage 1 decision class, overall score, "
                        "ambiguity penalty, and composer score."
                    ),
                ],
            )
            for index, record in enumerate(unique_records[:top_k_size])
        ]
        return TopKSummary(
            requested_k=top_k_size,
            returned_count=len(ranked),
            ranked_puzzles=ranked,
            notes=[
                ("Top-k ordering uses the Stage 1 policy: " + " > ".join(STAGE1_TOP_K_POLICY) + ".")
            ],
        )

    @staticmethod
    def _select_top_k_records(
        accepted_records: list[AcceptedPuzzleRecord],
        top_k: TopKSummary,
    ) -> list[AcceptedPuzzleRecord]:
        accepted_lookup: dict[str, AcceptedPuzzleRecord] = {}
        for record in accepted_records:
            accepted_lookup.setdefault(record.puzzle_id, record)
        return [
            accepted_lookup[ranked.puzzle_id]
            for ranked in top_k.ranked_puzzles
            if ranked.puzzle_id in accepted_lookup
        ]

    def _summary(
        self,
        run_id: str,
        output_dir: Path,
        accepted_records: list[AcceptedPuzzleRecord],
        rejected_records: list[RejectedPuzzleRecord],
        top_k: TopKSummary,
        calibration_summary: CalibrationSummary,
        *,
        candidate_group_type_counts: Counter[str] | None = None,
        candidate_board_mix_counts: Counter[str] | None = None,
        candidate_board_type_signature_counts: Counter[str] | None = None,
    ) -> BatchEvaluationSummary:
        total_generated = len(accepted_records) + len(rejected_records)
        reject_histogram = Counter(
            reason for record in rejected_records for reason in record.reject_reasons
        )
        group_type_counts = candidate_group_type_counts or Counter(
            group_type
            for record in accepted_records + rejected_records
            for group_type in record.group_types
        )
        generator_strategy_counts = Counter()
        for record in accepted_records + rejected_records:
            generators = record.selected_components.get("generators", [])
            if isinstance(generators, list):
                generator_strategy_counts.update(generators)
        board_mix_counts = candidate_board_mix_counts or Counter()
        board_type_signature_counts = candidate_board_type_signature_counts or Counter()
        if not candidate_board_mix_counts or not candidate_board_type_signature_counts:
            for record in accepted_records + rejected_records:
                if record.mixed_board:
                    board_mix_counts["mixed"] += 1
                elif set(record.group_types) == {"semantic"}:
                    board_mix_counts["semantic_only"] += 1
                else:
                    board_mix_counts["single_type_other"] += 1
                signature = "+".join(sorted(record.mechanism_mix_summary))
                board_type_signature_counts[signature] += 1

        all_breakdowns = [record.score_breakdown for record in accepted_records + rejected_records]
        overall_scores = [breakdown.overall for breakdown in all_breakdowns]
        coherence_scores = [breakdown.coherence for breakdown in all_breakdowns]
        ambiguity_penalties = [breakdown.ambiguity_penalty for breakdown in all_breakdowns]
        human_likeness_scores = [
            breakdown.human_likeness
            for breakdown in all_breakdowns
            if breakdown.human_likeness is not None
        ]

        ambiguity_risk_distribution = Counter(
            (
                record.ambiguity_report.risk_level.value
                if record.ambiguity_report is not None
                else "unknown"
            )
            for record in accepted_records + rejected_records
        )

        ensemble_results = [
            record.ensemble_result
            for record in accepted_records + rejected_records
            if record.ensemble_result is not None
        ]
        unanimous_target_match_count = sum(
            1
            for result in ensemble_results
            if (
                result.agreement_summary.matched_target_count
                == result.agreement_summary.total_solvers
            )
        )
        disagreement_count = sum(
            1 for result in ensemble_results if result.agreement_summary.disagreement_flags
        )
        average_agreement_ratio = (
            round(mean(result.agreement_summary.agreement_ratio for result in ensemble_results), 3)
            if ensemble_results
            else 0.0
        )

        return BatchEvaluationSummary(
            run_id=run_id,
            total_generated=total_generated,
            accepted_count=len(accepted_records),
            rejected_count=len(rejected_records),
            acceptance_rate=round((len(accepted_records) / max(total_generated, 1)), 3),
            reject_reason_histogram=RejectReasonHistogram(
                counts=dict(sorted(reject_histogram.items()))
            ),
            generator_mix=GeneratorMixSummary(
                group_type_counts=dict(sorted(group_type_counts.items())),
                generator_strategy_counts=dict(sorted(generator_strategy_counts.items())),
                board_mix_counts=dict(sorted(board_mix_counts.items())),
                board_type_signature_counts=dict(sorted(board_type_signature_counts.items())),
            ),
            score_distribution=ScoreDistributionSummary(
                average_overall=round(mean(overall_scores), 3) if overall_scores else 0.0,
                average_coherence=round(mean(coherence_scores), 3) if coherence_scores else 0.0,
                average_ambiguity_penalty=round(mean(ambiguity_penalties), 3)
                if ambiguity_penalties
                else 0.0,
                average_human_likeness=round(mean(human_likeness_scores), 3)
                if human_likeness_scores
                else 0.0,
                min_overall=min(overall_scores) if overall_scores else 0.0,
                max_overall=max(overall_scores) if overall_scores else 0.0,
            ),
            ambiguity_risk_distribution=dict(sorted(ambiguity_risk_distribution.items())),
            solver_agreement_statistics=SolverAgreementStatistics(
                total_ensemble_runs=len(ensemble_results),
                unanimous_target_match_count=unanimous_target_match_count,
                disagreement_count=disagreement_count,
                average_agreement_ratio=average_agreement_ratio,
            ),
            top_k=top_k,
            calibration_summary=calibration_summary,
            output_dir=str(output_dir),
            notes=[
                (
                    "Batch summary is built from demo-generation scaffolds."
                    if self._settings.demo_mode
                    else (
                        "Batch summary is built from the Stage 3 mixed-generation "
                        "path plus the Stage 1 quality-control core and "
                        "Stage 3 style-analysis artifacts."
                    )
                ),
                (
                    "Generator mix reflects the candidate boards evaluated within each request, "
                    "not just the final selected winners."
                ),
            ],
        )

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def evaluate_batch(self, config: BatchEvaluationConfig) -> BatchEvaluationRun:
        """Run a batch evaluation and persist the resulting artifacts."""

        if config.demo_mode != self._settings.demo_mode:
            raise RuntimeError(
                "BatchEvaluationConfig.demo_mode must match Settings.demo_mode "
                "so the configured pipeline and artifact labels stay honest."
            )

        run_id = new_id("eval")
        output_dir = (
            Path(config.output_dir) if config.output_dir else self._settings.eval_runs_dir / run_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        accepted_records: list[AcceptedPuzzleRecord] = []
        rejected_records: list[RejectedPuzzleRecord] = []
        trace_payloads: list[dict[str, object]] = []
        candidate_group_type_counts: Counter[str] = Counter()
        candidate_board_mix_counts: Counter[str] = Counter()
        candidate_board_type_signature_counts: Counter[str] = Counter()

        for iteration_index in range(config.num_puzzles):
            request_seed = config.base_seed + iteration_index
            request = PuzzleGenerationRequest(
                seed=request_seed,
                include_trace=config.save_traces,
                developer_mode=config.save_traces,
            )
            run_result = self._generation_service.run_generation(request)
            response = SimpleNamespace(
                demo_mode=self._settings.demo_mode,
                selected_components={
                    "feature_extractor": run_result.components.feature_extractor,
                    "generators": run_result.components.generators,
                    "composer": run_result.components.composer,
                    "solver": run_result.components.solver,
                    "solver_registry": run_result.components.solver_registry,
                    "verifier": run_result.components.verifier,
                    "scorer": run_result.components.scorer,
                    "style_analyzer": run_result.components.style_analyzer or "not_configured",
                },
                warnings=run_result.warnings,
                puzzle=run_result.puzzle,
                verification=run_result.verification,
                score=run_result.score,
                trace=run_result.trace,
            )
            for candidate in run_result.candidate_results:
                candidate_group_type_counts.update(
                    group.group_type.value for group in candidate.puzzle.groups
                )
                if candidate.puzzle.metadata.get("mixed_board"):
                    candidate_board_mix_counts["mixed"] += 1
                elif {group.group_type.value for group in candidate.puzzle.groups} == {"semantic"}:
                    candidate_board_mix_counts["semantic_only"] += 1
                else:
                    candidate_board_mix_counts["single_type_other"] += 1
                candidate_signature = "+".join(
                    sorted(candidate.puzzle.metadata.get("mechanism_mix_summary", {}))
                )
                if candidate_signature:
                    candidate_board_type_signature_counts[candidate_signature] += 1
            if response.verification.passed:
                accepted_records.append(
                    self._accepted_record(response, iteration_index, request_seed)
                )
            else:
                rejected_records.append(
                    self._rejected_record(response, iteration_index, request_seed)
                )

            if config.save_traces and response.trace is not None:
                trace_payloads.append(response.trace.model_dump(mode="json"))

        top_k = self._rank_top_k(accepted_records, config.top_k_size)
        top_k_records = self._select_top_k_records(accepted_records, top_k)
        calibration_summary = build_batch_calibration_summary(
            accepted_records=accepted_records,
            rejected_records=rejected_records,
            top_k_records=top_k_records,
        )
        summary = self._summary(
            run_id,
            output_dir,
            accepted_records,
            rejected_records,
            top_k,
            calibration_summary,
            candidate_group_type_counts=candidate_group_type_counts,
            candidate_board_mix_counts=candidate_board_mix_counts,
            candidate_board_type_signature_counts=candidate_board_type_signature_counts,
        )
        calibration_payloads = build_calibration_artifact_payloads(calibration_summary)

        output_files = {
            "config": str(output_dir / "config.json"),
            "summary": str(output_dir / "summary.json"),
            "accepted": str(output_dir / "accepted.json"),
            "rejected": str(output_dir / "rejected.json"),
            "top_k": str(output_dir / "top_k.json"),
            "calibration_summary": str(output_dir / "calibration_summary.json"),
            "style_summary": str(output_dir / "style_summary.json"),
            "mechanism_mix_summary": str(output_dir / "mechanism_mix_summary.json"),
            "threshold_diagnostics": str(output_dir / "threshold_diagnostics.json"),
        }
        if config.save_traces:
            output_files["traces"] = str(output_dir / "traces.json")

        run = BatchEvaluationRun(
            run_id=run_id,
            config=config,
            summary=summary,
            accepted_records=accepted_records,
            rejected_records=rejected_records,
            output_files=output_files,
        )

        self._write_json(Path(output_files["config"]), config.model_dump(mode="json"))
        self._write_json(Path(output_files["summary"]), summary.model_dump(mode="json"))
        self._write_json(
            Path(output_files["accepted"]),
            [record.model_dump(mode="json") for record in accepted_records],
        )
        self._write_json(
            Path(output_files["rejected"]),
            [record.model_dump(mode="json") for record in rejected_records],
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
        if config.save_traces:
            self._write_json(Path(output_files["traces"]), trace_payloads)

        return run

    def load_latest_debug_view(self) -> DebugComparisonView | None:
        """Load the latest available batch evaluation summary and top-k view."""

        eval_runs_dir = self._settings.eval_runs_dir
        if not eval_runs_dir.exists():
            return None

        candidate_dirs = [path for path in eval_runs_dir.iterdir() if path.is_dir()]
        if not candidate_dirs:
            return None

        latest_dir = max(candidate_dirs, key=lambda path: path.stat().st_mtime)
        summary_path = latest_dir / "summary.json"
        top_k_path = latest_dir / "top_k.json"
        if not summary_path.exists() or not top_k_path.exists():
            return None

        with summary_path.open("r", encoding="utf-8") as handle:
            summary = BatchEvaluationSummary.model_validate(json.load(handle))
        with top_k_path.open("r", encoding="utf-8") as handle:
            top_k = TopKSummary.model_validate(json.load(handle))

        return DebugComparisonView(
            run_id=summary.run_id,
            summary=summary,
            top_k=top_k,
            notes=[
                "Latest debug comparison view loaded from persisted batch evaluation artifacts.",
            ],
        )
