"""Helpers for local NYT benchmark normalization and quality auditing."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.features.semantic_baseline import normalize_signal
from app.schemas.benchmark_models import (
    BenchmarkGroupRecord,
    BenchmarkManifest,
    BenchmarkNormalizationResult,
    BenchmarkSplitManifest,
    NormalizedBenchmarkBoard,
    QualityAuditReport,
)
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    CandidatePoolPuzzleRecord,
    RejectedPuzzleRecord,
    ScoreBreakdownView,
    TopKSummary,
)
from app.schemas.feature_models import WordEntry
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.scoring.calibration import build_batch_slice_summary
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.solver.base import BaseSolverBackend
from app.solver.verifier import InternalPuzzleVerifier
from app.utils.ids import stable_id

LEVEL_TO_COLOR = {
    0: "yellow",
    1: "green",
    2: "blue",
    3: "purple",
}

PHONETIC_LABEL_HINTS = (
    "rhyme",
    "homophone",
    "sounds like",
    "pronunciation",
)
LEXICAL_LABEL_HINTS = (
    "starts with",
    "start with",
    "ends with",
    "ending with",
    "prefix",
    "suffix",
    "contains",
    "spelled",
    "anagram",
    "before ",
    "after ",
)
THEME_LABEL_HINTS = (
    "nba",
    "nfl",
    "mlb",
    "nhl",
    "movie",
    "film",
    "tv",
    "television",
    "song",
    "album",
    "book",
    "novel",
    "character",
    "characters",
    "pokemon",
    "disney",
    "shakespeare",
    "mythology",
    "brand",
    "company",
    "companies",
    "superhero",
)
QUALITY_BUCKETS = (
    "accepted_high_confidence",
    "accepted_borderline",
    "rejected",
)


class ReferenceAnswerSolverBackend(BaseSolverBackend):
    """Answer-aware solver used only for benchmark-side offline audit."""

    backend_name = "benchmark_reference_answer_solver"

    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext):  # type: ignore[override]
        from app.schemas.puzzle_models import SolverResult

        return SolverResult(
            backend_name=self.backend_name,
            solved=True,
            confidence=1.0,
            proposed_groups=[list(group.words) for group in puzzle.groups],
            alternative_groupings_detected=0,
            notes=[
                "Reference answer solver returns the known benchmark grouping.",
                "Used only for offline benchmark audit, never for generation ranking.",
            ],
            raw_output={"benchmark_reference": True},
        )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _clean_word(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_words(words: list[str]) -> list[str]:
    return [_clean_word(word) for word in words if _clean_word(word)]


def _board_id(puzzle_date: str, source_game_id: str) -> str:
    return f"nyt_connections_{puzzle_date}_{source_game_id}"


def _board_signature(words: list[str]) -> str:
    return stable_id("benchmark_board", sorted(normalize_signal(word) for word in words))


def _solution_signature(groups: list[BenchmarkGroupRecord]) -> str:
    payload = [
        {
            "level": group.level,
            "label": normalize_signal(group.group_label),
            "words": sorted(normalize_signal(word) for word in group.words),
        }
        for group in sorted(groups, key=lambda item: (item.level or 99, item.group_label))
    ]
    return stable_id("benchmark_solution", payload)


def _counts_to_shares(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {key: round(value / total, 4) for key, value in sorted(counts.items())}


def _quality_bucket(decision: str | None) -> str:
    if decision == "accept":
        return "accepted_high_confidence"
    if decision == "borderline":
        return "accepted_borderline"
    return "rejected"


def _quality_bucket_counts(decisions: list[str | None]) -> dict[str, int]:
    counts = {name: 0 for name in QUALITY_BUCKETS}
    for decision in decisions:
        counts[_quality_bucket(decision)] += 1
    return counts


def _shared_prefix(words: list[str], width: int) -> str:
    if not words or any(len(word) < width for word in words):
        return ""
    prefix = words[0][:width]
    if all(word.startswith(prefix) for word in words):
        return prefix
    return ""


def _shared_suffix(words: list[str], width: int) -> str:
    if not words or any(len(word) < width for word in words):
        return ""
    suffix = words[0][-width:]
    if all(word.endswith(suffix) for word in words):
        return suffix
    return ""


def _infer_group_mechanism(label: str, words: list[str]) -> tuple[str, float, str]:
    normalized_label = label.lower()
    lowered_words = [word.lower() for word in words]

    if any(token in normalized_label for token in PHONETIC_LABEL_HINTS):
        return "phonetic", 0.95, "Label explicitly references rhyme or homophone wordplay."
    if any(token in normalized_label for token in LEXICAL_LABEL_HINTS):
        return "lexical", 0.9, "Label explicitly references a spelling or substring pattern."

    shared_prefix = _shared_prefix(lowered_words, 2) or _shared_prefix(lowered_words, 3)
    if shared_prefix:
        return "lexical", 0.78, f"All members share the prefix '{shared_prefix.upper()}'."

    shared_suffix = _shared_suffix(lowered_words, 2) or _shared_suffix(lowered_words, 3)
    if shared_suffix:
        return "lexical", 0.78, f"All members share the suffix '{shared_suffix.upper()}'."

    if any(token in normalized_label for token in THEME_LABEL_HINTS):
        return "theme", 0.7, "Label looks like a named-domain or trivia/theme reference."

    return "semantic", 0.6, "Defaulted to semantic because no stronger mechanism cue was found."


def _group_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positions = []
    for row in sorted(rows, key=lambda item: (item["Starting Row"], item["Starting Column"])):
        positions.append(
            {
                "word": _clean_word(row.get("Word")),
                "row": int(row["Starting Row"]),
                "column": int(row["Starting Column"]),
            }
        )
    return positions


def _board_rows(df: pd.DataFrame, game_id: int) -> list[dict[str, Any]]:
    subset = df[df["Game ID"] == game_id].copy()
    subset = subset.sort_values(["Starting Row", "Starting Column", "Group Level", "Group Name"])
    return subset.to_dict(orient="records")


def _load_primary_rows(raw_dir: Path) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    load_notes: list[str] = []
    manifest = {}
    manifest_path = raw_dir / "source_manifest.json"
    if manifest_path.exists():
        manifest = dict(_read_json(manifest_path))

    parquet_path = raw_dir / "nyt_connections_hf.parquet"
    csv_path = raw_dir / "nyt_connections_hf.csv"
    if parquet_path.exists():
        try:
            frame = pd.read_parquet(parquet_path)
            load_notes.append("parquet_loaded")
            return frame, load_notes, manifest
        except Exception as exc:  # pragma: no cover - exercised by fixture fallback
            load_notes.append("csv_fallback_used")
            load_notes.append(f"csv_fallback_used:{type(exc).__name__}")
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing primary raw dataset under {raw_dir}.")
    frame = pd.read_csv(csv_path)
    load_notes.append("csv_loaded")
    return frame, load_notes, manifest


def _normalize_primary_board(
    rows: list[dict[str, Any]],
    *,
    source_dataset: str,
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    puzzle_date = str(rows[0]["Puzzle Date"])
    source_game_id = str(rows[0]["Game ID"])
    grouped_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_rows[int(row["Group Level"])].append(row)

    groups: list[dict[str, Any]] = []
    board_positions = []
    for row in sorted(rows, key=lambda item: (item["Starting Row"], item["Starting Column"])):
        word = _clean_word(row.get("Word"))
        board_positions.append(
            {
                "word": word,
                "row": int(row["Starting Row"]),
                "column": int(row["Starting Column"]),
                "level": int(row["Group Level"]),
                "group_label": str(row["Group Name"]).strip(),
            }
        )

    for level in sorted(grouped_rows):
        level_rows = grouped_rows[level]
        label_values = sorted(
            {str(item["Group Name"]).strip() for item in level_rows if item["Group Name"]}
        )
        label = label_values[0] if label_values else f"LEVEL {level}"
        words = _normalize_words([_clean_word(item.get("Word")) for item in level_rows])
        if len(words) != 4:
            issues.append(f"group_level_{level}_word_count")
        mechanism_type, mechanism_confidence, mechanism_rationale = _infer_group_mechanism(
            label,
            words,
        )
        groups.append(
            {
                "group_label": label,
                "level": level,
                "color": LEVEL_TO_COLOR.get(level),
                "words": words,
                "original_positions": _group_positions(level_rows),
                "mechanism_type": mechanism_type,
                "mechanism_confidence": mechanism_confidence,
                "mechanism_rationale": mechanism_rationale,
                "metadata": {"source_dataset": source_dataset},
            }
        )

    board_words = _normalize_words([position["word"] for position in board_positions])
    if len(board_words) != 16:
        issues.append("board_word_count")
    if len(set(board_words)) != len(board_words):
        issues.append("duplicate_board_words")
    if len(groups) != 4:
        issues.append("group_count")

    return (
        {
            "benchmark_board_id": _board_id(puzzle_date, source_game_id),
            "source_dataset": source_dataset,
            "source_provenance": ["hf_primary"],
            "source_game_id": source_game_id,
            "puzzle_date": puzzle_date,
            "board_words": board_words,
            "original_tile_positions": board_positions,
            "groups": groups,
            "metadata": {"integrity_issues": issues},
        },
        issues,
    )


def _normalize_supplement_board(item: dict[str, Any]) -> NormalizedBenchmarkBoard:
    puzzle_date = str(item["date"])
    source_game_id = str(item["id"])
    groups: list[BenchmarkGroupRecord] = []
    board_words: list[str] = []
    for answer in sorted(
        item.get("answers", []), key=lambda row: (row.get("level", 99), row.get("group", ""))
    ):
        level = int(answer["level"]) if answer.get("level") is not None else None
        words = _normalize_words(list(answer.get("members", [])))
        if len(words) != 4 or len(set(words)) != 4:
            raise ValueError(
                f"Supplement board {source_game_id} group '{answer.get('group', '')}' is invalid."
            )
        mechanism_type, mechanism_confidence, mechanism_rationale = _infer_group_mechanism(
            str(answer.get("group", "")),
            words,
        )
        groups.append(
            BenchmarkGroupRecord(
                group_label=str(answer.get("group", "")).strip(),
                level=level,
                color=LEVEL_TO_COLOR.get(level) if level is not None else None,
                words=words,
                mechanism_type=mechanism_type,
                mechanism_confidence=mechanism_confidence,
                mechanism_rationale=mechanism_rationale,
                metadata={"supplement_only": True},
            )
        )
        board_words.extend(words)

    if len(groups) != 4:
        raise ValueError(f"Supplement board {source_game_id} does not contain four valid groups.")

    board = NormalizedBenchmarkBoard(
        benchmark_board_id=_board_id(puzzle_date, source_game_id),
        source_dataset="github_json_supplement",
        source_provenance=["github_json_supplement"],
        source_game_id=source_game_id,
        puzzle_date=puzzle_date,
        board_words=board_words,
        original_tile_positions=[],
        groups=groups,
        board_signature=_board_signature(board_words),
        solution_signature=_solution_signature(groups),
        metadata={"supplement_only": True},
    )
    return board


def _repair_primary_board(
    primary_payload: dict[str, Any],
    supplement_board: NormalizedBenchmarkBoard,
) -> NormalizedBenchmarkBoard:
    board_positions = list(primary_payload["original_tile_positions"])
    supplement_words_by_level = {
        group.level: list(group.words)
        for group in supplement_board.groups
        if group.level is not None
    }

    repaired_groups: list[BenchmarkGroupRecord] = []
    for group_payload in primary_payload["groups"]:
        level = group_payload["level"]
        fallback_words = supplement_words_by_level.get(level, [])
        positions = sorted(
            list(group_payload.get("original_positions", [])),
            key=lambda item: (item["row"], item["column"]),
        )
        existing_words = [
            _clean_word(position["word"]) for position in positions if _clean_word(position["word"])
        ]
        missing_words = sorted(set(fallback_words) - set(existing_words))
        missing_iter = iter(missing_words)
        repaired_words: list[str] = []
        repaired_positions: list[dict[str, Any]] = []
        for position in positions:
            word = _clean_word(position["word"])
            if not word:
                word = next(missing_iter, "")
            repaired_words.append(word)
            repaired_positions.append({**position, "word": word})
        if len(repaired_words) != 4 or len(set(repaired_words)) != 4:
            repaired_words = list(fallback_words)
        mechanism_type, mechanism_confidence, mechanism_rationale = _infer_group_mechanism(
            group_payload["group_label"],
            repaired_words,
        )
        repaired_groups.append(
            BenchmarkGroupRecord(
                group_label=group_payload["group_label"],
                level=level,
                color=group_payload["color"],
                words=repaired_words,
                original_positions=repaired_positions,
                mechanism_type=mechanism_type,
                mechanism_confidence=mechanism_confidence,
                mechanism_rationale=mechanism_rationale,
                metadata={
                    "repaired_from_supplement": True,
                    "supplement_board_id": supplement_board.benchmark_board_id,
                },
            )
        )

    repaired_positions = []
    repaired_group_lookup = {(group.level, group.group_label): group for group in repaired_groups}
    for position in board_positions:
        group = repaired_group_lookup.get((position["level"], position["group_label"]))
        replacement = ""
        if group is not None:
            matching = next(
                (
                    item["word"]
                    for item in group.original_positions
                    if item["row"] == position["row"] and item["column"] == position["column"]
                ),
                "",
            )
            replacement = matching
        repaired_positions.append(
            {**position, "word": replacement or _clean_word(position["word"])}
        )

    board_words = _normalize_words([item["word"] for item in repaired_positions])
    repaired_board = NormalizedBenchmarkBoard(
        benchmark_board_id=primary_payload["benchmark_board_id"],
        source_dataset=primary_payload["source_dataset"],
        source_provenance=["hf_primary", "github_repair"],
        source_game_id=primary_payload["source_game_id"],
        puzzle_date=primary_payload["puzzle_date"],
        board_words=board_words,
        original_tile_positions=repaired_positions,
        groups=repaired_groups,
        board_signature=_board_signature(board_words),
        solution_signature=_solution_signature(repaired_groups),
        metadata={"repaired_from_supplement": True},
    )
    return repaired_board


def _build_split(
    *,
    split_name: str,
    policy: str,
    boards: list[NormalizedBenchmarkBoard],
    notes: list[str] | None = None,
) -> BenchmarkSplitManifest:
    board_ids = [board.benchmark_board_id for board in boards]
    return BenchmarkSplitManifest(
        split_name=split_name,
        policy=policy,
        board_ids=board_ids,
        count=len(board_ids),
        start_date=boards[0].puzzle_date if boards else None,
        end_date=boards[-1].puzzle_date if boards else None,
        notes=notes or [],
    )


def normalize_public_benchmark(
    *,
    raw_dir: Path,
    normalized_dir: Path,
) -> BenchmarkNormalizationResult:
    """Normalize local raw NYT benchmark files into deterministic board records."""

    frame, load_notes, manifest_payload = _load_primary_rows(raw_dir)
    source_dataset = str(manifest_payload.get("dataset_id", "eric27n/NYT-Connections"))
    primary_payloads: list[dict[str, Any]] = []
    invalid_board_ids: list[str] = []
    repaired_board_count = 0

    for game_id in sorted(frame["Game ID"].dropna().astype(int).unique().tolist()):
        payload, issues = _normalize_primary_board(
            _board_rows(frame, game_id), source_dataset=source_dataset
        )
        primary_payloads.append(payload)
        if issues:
            invalid_board_ids.append(payload["benchmark_board_id"])

    supplement_boards: dict[str, NormalizedBenchmarkBoard] = {}
    supplement_path = raw_dir / "nyt_connections_answers_github.json"
    if supplement_path.exists():
        supplement_items = list(_read_json(supplement_path))
        for item in supplement_items:
            try:
                board = _normalize_supplement_board(dict(item))
            except ValueError as exc:
                invalid_board_ids.append(_board_id(str(item.get("date")), str(item.get("id"))))
                load_notes.append(
                    f"skipped_invalid_supplement:{item.get('id')}:{type(exc).__name__}"
                )
                continue
            supplement_boards[board.benchmark_board_id] = board

    normalized_boards: list[NormalizedBenchmarkBoard] = []
    for payload in primary_payloads:
        issues = list(payload["metadata"].get("integrity_issues", []))
        board_id = payload["benchmark_board_id"]
        if issues:
            supplement_board = supplement_boards.get(board_id)
            if supplement_board is None:
                continue
            normalized_boards.append(_repair_primary_board(payload, supplement_board))
            repaired_board_count += 1
            continue

        groups = [BenchmarkGroupRecord(**group) for group in payload["groups"]]
        board_words = payload["board_words"]
        normalized_boards.append(
            NormalizedBenchmarkBoard(
                benchmark_board_id=board_id,
                source_dataset=payload["source_dataset"],
                source_provenance=payload["source_provenance"],
                source_game_id=payload["source_game_id"],
                puzzle_date=payload["puzzle_date"],
                board_words=board_words,
                original_tile_positions=payload["original_tile_positions"],
                groups=groups,
                board_signature=_board_signature(board_words),
                solution_signature=_solution_signature(groups),
                metadata={"integrity_issues": []},
            )
        )

    primary_sorted = sorted(
        normalized_boards,
        key=lambda board: (board.puzzle_date, board.benchmark_board_id),
    )
    primary_max_date = primary_sorted[-1].puzzle_date if primary_sorted else None
    supplement_only = [
        board
        for board in supplement_boards.values()
        if board.benchmark_board_id not in {item.benchmark_board_id for item in primary_sorted}
        and (primary_max_date is None or board.puzzle_date > primary_max_date)
    ]
    supplement_only = sorted(
        supplement_only,
        key=lambda board: (board.puzzle_date, board.benchmark_board_id),
    )

    merged_boards = sorted(
        primary_sorted + supplement_only,
        key=lambda board: (board.puzzle_date, board.benchmark_board_id),
    )

    holdout_count = 1 if len(primary_sorted) <= 1 else max(1, math.ceil(len(primary_sorted) * 0.2))
    calibration_count = max(0, len(primary_sorted) - holdout_count)
    calibration_boards = primary_sorted[:calibration_count]
    holdout_boards = primary_sorted[calibration_count:]
    calibration_split = _build_split(
        split_name="calibration",
        policy="Oldest 80% of primary benchmark boards by puzzle_date, benchmark_board_id.",
        boards=calibration_boards,
        notes=["Primary Hugging Face benchmark only."],
    )
    holdout_split = _build_split(
        split_name="holdout",
        policy="Newest 20% of primary benchmark boards by puzzle_date, benchmark_board_id.",
        boards=holdout_boards,
        notes=["Primary Hugging Face benchmark only."],
    )
    freshness_split = (
        _build_split(
            split_name="freshness",
            policy="Supplement-only boards newer than the primary benchmark max date.",
            boards=supplement_only,
            notes=["Supplemental GitHub mirror boards."],
        )
        if supplement_only
        else None
    )

    normalized_dir.mkdir(parents=True, exist_ok=True)
    output_files = {
        "boards_jsonl": str(normalized_dir / "boards_v1.jsonl"),
        "boards_parquet": str(normalized_dir / "boards_v1.parquet"),
        "manifest": str(normalized_dir / "benchmark_manifest.json"),
        "calibration_split": str(normalized_dir / "calibration_split.json"),
        "holdout_split": str(normalized_dir / "holdout_split.json"),
    }
    if freshness_split is not None:
        output_files["freshness_split"] = str(normalized_dir / "freshness_split.json")

    manifest = BenchmarkManifest(
        primary_source_dataset=source_dataset,
        board_count=len(merged_boards),
        primary_board_count=len(primary_sorted),
        supplement_board_count=len(supplement_only),
        repaired_board_count=repaired_board_count,
        invalid_board_ids=sorted(invalid_board_ids),
        load_notes=load_notes,
        date_min=merged_boards[0].puzzle_date if merged_boards else None,
        date_max=merged_boards[-1].puzzle_date if merged_boards else None,
        split_policy=(
            "primary oldest 80% calibration / newest 20% holdout; "
            "newer supplement-only boards freshness split"
        ),
        artifact_paths=output_files,
        notes=[
            "Primary benchmark source remains the local Hugging Face export.",
            (
                "Supplement data only repairs missing fields or adds newer "
                "explicitly supplemental boards."
            ),
        ],
    )

    _write_jsonl(
        Path(output_files["boards_jsonl"]),
        [board.model_dump(mode="json") for board in merged_boards],
    )
    pd.DataFrame(
        {
            "benchmark_board_id": [board.benchmark_board_id for board in merged_boards],
            "source_dataset": [board.source_dataset for board in merged_boards],
            "puzzle_date": [board.puzzle_date for board in merged_boards],
            "source_game_id": [board.source_game_id for board in merged_boards],
            "board_words_json": [json.dumps(board.board_words) for board in merged_boards],
            "groups_json": [
                json.dumps([group.model_dump(mode="json") for group in board.groups])
                for board in merged_boards
            ],
            "board_signature": [board.board_signature for board in merged_boards],
            "solution_signature": [board.solution_signature for board in merged_boards],
        }
    ).to_parquet(Path(output_files["boards_parquet"]), index=False)
    _write_json(Path(output_files["manifest"]), manifest.model_dump(mode="json"))
    _write_json(Path(output_files["calibration_split"]), calibration_split.model_dump(mode="json"))
    _write_json(Path(output_files["holdout_split"]), holdout_split.model_dump(mode="json"))
    if freshness_split is not None:
        _write_json(Path(output_files["freshness_split"]), freshness_split.model_dump(mode="json"))

    return BenchmarkNormalizationResult(
        manifest=manifest,
        boards=merged_boards,
        calibration_split=calibration_split,
        holdout_split=holdout_split,
        freshness_split=freshness_split,
        output_files=output_files,
    )


def load_normalized_benchmark(normalized_dir: Path) -> list[NormalizedBenchmarkBoard]:
    """Load normalized benchmark boards from the canonical JSONL artifact."""

    boards: list[NormalizedBenchmarkBoard] = []
    with (normalized_dir / "boards_v1.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            boards.append(NormalizedBenchmarkBoard.model_validate_json(line))
    return sorted(boards, key=lambda board: (board.puzzle_date, board.benchmark_board_id))


def _load_split(normalized_dir: Path, filename: str) -> BenchmarkSplitManifest | None:
    path = normalized_dir / filename
    if not path.exists():
        return None
    return BenchmarkSplitManifest.model_validate(_read_json(path))


def _load_generated_run(
    run_dir: Path,
) -> tuple[
    dict[str, Any],
    TopKSummary,
    list[AcceptedPuzzleRecord],
    list[RejectedPuzzleRecord],
    list[CandidatePoolPuzzleRecord],
]:
    summary = dict(_read_json(run_dir / "summary.json"))
    top_k = TopKSummary.model_validate(_read_json(run_dir / "top_k.json"))
    accepted = [
        AcceptedPuzzleRecord.model_validate(item)
        for item in list(_read_json(run_dir / "accepted.json"))
    ]
    rejected = [
        RejectedPuzzleRecord.model_validate(item)
        for item in list(_read_json(run_dir / "rejected.json"))
    ]
    candidate_pool_path = run_dir / "candidate_pool.json"
    candidate_pool = (
        [
            CandidatePoolPuzzleRecord.model_validate(item)
            for item in list(_read_json(candidate_pool_path))
        ]
        if candidate_pool_path.exists()
        else []
    )
    return summary, top_k, accepted, rejected, candidate_pool


def _benchmark_group_candidate(
    board: NormalizedBenchmarkBoard,
    group: BenchmarkGroupRecord,
    word_ids_by_word: dict[str, str],
) -> GroupCandidate:
    label_tokens = [token for token in normalize_signal(group.group_label).split("_") if token]
    evidence_key = "member_scores"
    if group.mechanism_type == "lexical":
        evidence_key = "word_matches"
    elif group.mechanism_type == "phonetic":
        evidence_key = "pronunciation_membership"
    elif group.mechanism_type == "theme":
        evidence_key = "membership"

    return GroupCandidate(
        candidate_id=stable_id("benchmark_group", board.benchmark_board_id, group.group_label),
        group_type=GroupType(group.mechanism_type),
        label=group.group_label,
        rationale="Normalized external benchmark group used for offline audit.",
        words=list(group.words),
        word_ids=[word_ids_by_word[word] for word in group.words],
        source_strategy="nyt_public_benchmark",
        extraction_mode="benchmark_normalized_v1",
        confidence=1.0,
        metadata={
            "normalized_label": normalize_signal(group.group_label),
            "rule_signature": stable_id(
                "benchmark_rule",
                board.benchmark_board_id,
                group.group_label,
                sorted(group.words),
            ),
            "shared_tags": label_tokens,
            "evidence": {
                "shared_signals": label_tokens,
                evidence_key: [
                    {"word": word, "source": "benchmark_normalized_v1"} for word in group.words
                ],
            },
            "mechanism_inference_confidence": group.mechanism_confidence,
            "mechanism_inference_rationale": group.mechanism_rationale,
        },
    )


def _benchmark_puzzle_context(
    board: NormalizedBenchmarkBoard,
) -> tuple[PuzzleCandidate, GenerationContext]:
    word_entries: list[WordEntry] = []
    word_ids_by_word: dict[str, str] = {}
    group_lookup = {word: group for group in board.groups for word in group.words}
    for word in board.board_words:
        group = group_lookup[word]
        word_id = stable_id("benchmark_word", board.benchmark_board_id, word)
        word_ids_by_word[word] = word_id
        word_entries.append(
            WordEntry(
                word_id=word_id,
                surface_form=word,
                normalized=normalize_signal(word),
                source=board.source_dataset,
                known_group_hints={group.mechanism_type: group.group_label},
                metadata={"seed_group_label": group.group_label},
            )
        )

    features = HumanCuratedFeatureExtractor().extract_features(word_entries)
    features_by_word_id = {feature.word_id: feature for feature in features}
    groups = [_benchmark_group_candidate(board, group, word_ids_by_word) for group in board.groups]
    puzzle = PuzzleCandidate(
        puzzle_id=board.benchmark_board_id,
        board_words=list(board.board_words),
        groups=groups,
        metadata={
            "mechanism_mix_summary": dict(Counter(group.group_type.value for group in groups))
        },
    )
    context = GenerationContext(
        request_id=stable_id("benchmark_request", board.benchmark_board_id),
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=False,
        requested_group_types=GroupType.ordered(),
        run_metadata={"features_by_word_id": features_by_word_id},
    )
    return puzzle, context


def _score_breakdown_view(score) -> ScoreBreakdownView:
    return ScoreBreakdownView(
        overall=score.overall,
        coherence=score.coherence,
        ambiguity_penalty=score.ambiguity_penalty,
        human_likeness=score.human_likeness,
        components=score.components,
    )


def _record_from_benchmark_board(
    board: NormalizedBenchmarkBoard,
) -> AcceptedPuzzleRecord | RejectedPuzzleRecord:
    puzzle, context = _benchmark_puzzle_context(board)
    verifier = InternalPuzzleVerifier(solver=ReferenceAnswerSolverBackend())
    verification = verifier.verify(puzzle, context)
    score = HumanOwnedPuzzleScorer().score(puzzle, verification, context)
    base_payload = {
        "iteration_index": 0,
        "request_seed": 0,
        "puzzle_id": board.benchmark_board_id,
        "board_words": list(board.board_words),
        "group_labels": [group.group_label for group in board.groups],
        "group_word_sets": [list(group.words) for group in board.groups],
        "group_types": [group.mechanism_type for group in board.groups],
        "mechanism_mix_summary": dict(Counter(group.mechanism_type for group in board.groups)),
        "mixed_board": len({group.mechanism_type for group in board.groups}) > 1,
        "verification_decision": verification.decision.value,
        "score_breakdown": _score_breakdown_view(score),
        "ambiguity_report": verification.ambiguity_report,
        "ensemble_result": verification.ensemble_result,
        "style_analysis": score.style_analysis,
        "notes": [
            "Benchmark board re-evaluated with answer-aware solver and heuristic mechanism labels.",
        ],
    }
    if verification.decision.value == "reject":
        return RejectedPuzzleRecord(
            **base_payload,
            reject_reasons=[reason.code.value for reason in verification.reject_reasons],
        )
    return AcceptedPuzzleRecord(**base_payload)


def _slice_records_by_ids(
    boards: list[NormalizedBenchmarkBoard],
    split: BenchmarkSplitManifest | None,
) -> list[AcceptedPuzzleRecord | RejectedPuzzleRecord]:
    if split is None or not split.board_ids:
        return []
    board_lookup = {board.benchmark_board_id: board for board in boards}
    return [_record_from_benchmark_board(board_lookup[board_id]) for board_id in split.board_ids]


def _top_k_records(
    accepted_records: list[AcceptedPuzzleRecord],
    top_k_summary: TopKSummary,
    candidate_pool_records: list[CandidatePoolPuzzleRecord] | None = None,
) -> list[AcceptedPuzzleRecord]:
    accepted_lookup: dict[str, AcceptedPuzzleRecord] = {}
    for record in accepted_records:
        accepted_lookup.setdefault(record.puzzle_id, record)
    for record in candidate_pool_records or []:
        if record.verification_decision == "reject":
            continue
        accepted_lookup.setdefault(
            record.puzzle_id,
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
            ),
        )
    return [
        accepted_lookup[ranked.puzzle_id]
        for ranked in top_k_summary.ranked_puzzles
        if ranked.puzzle_id in accepted_lookup
    ]


def _score_summary(
    records: list[AcceptedPuzzleRecord | RejectedPuzzleRecord],
) -> dict[str, float]:
    if not records:
        return {}
    overall = [record.score_breakdown.overall for record in records]
    coherence = [record.score_breakdown.coherence for record in records]
    ambiguity = [record.score_breakdown.ambiguity_penalty for record in records]
    human_likeness = [
        record.score_breakdown.human_likeness
        for record in records
        if record.score_breakdown.human_likeness is not None
    ]
    return {
        "overall_mean": round(mean(overall), 4),
        "coherence_mean": round(mean(coherence), 4),
        "ambiguity_penalty_mean": round(mean(ambiguity), 4),
        "human_likeness_mean": round(mean(human_likeness), 4) if human_likeness else 0.0,
    }


def _ambiguity_summary(
    records: list[AcceptedPuzzleRecord | RejectedPuzzleRecord],
) -> dict[str, float]:
    if not records:
        return {}
    board_pressure = []
    leakage = []
    alt_pressure = []
    for record in records:
        leakage.append(
            float(record.ambiguity_report.penalty_hint) if record.ambiguity_report else 0.0
        )
        if record.ambiguity_report and record.ambiguity_report.evidence.board_summary is not None:
            board_pressure.append(
                float(record.ambiguity_report.evidence.board_summary.board_pressure)
            )
            alt_pressure.append(
                float(record.ambiguity_report.evidence.board_summary.max_alternative_group_pressure)
            )
        else:
            board_pressure.append(0.0)
            alt_pressure.append(0.0)
    return {
        "board_pressure_mean": round(mean(board_pressure), 4),
        "leakage_penalty_mean": round(mean(leakage), 4),
        "alternative_group_pressure_mean": round(mean(alt_pressure), 4),
    }


def _comparison_deltas(
    generated: dict[str, float],
    benchmark: dict[str, float],
) -> dict[str, dict[str, float]]:
    metrics = sorted(set(generated) | set(benchmark))
    return {
        metric: {
            "generated": round(float(generated.get(metric, 0.0)), 4),
            "benchmark": round(float(benchmark.get(metric, 0.0)), 4),
            "absolute_delta": round(
                abs(float(generated.get(metric, 0.0)) - float(benchmark.get(metric, 0.0))), 4
            ),
        }
        for metric in metrics
    }


def _l1_distance(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    return round(
        sum(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in keys), 4
    )


def _benchmark_anchor_metric_summary(
    slice_summary,
    score_summary: dict[str, float],
) -> dict[str, float]:
    return {
        **slice_summary.style_metric_averages,
        **slice_summary.board_diversity_summary,
        **slice_summary.label_shape_summary,
        **score_summary,
    }


def _style_metric_inflation_flags(
    generated_metrics: dict[str, float],
    benchmark_metrics: dict[str, float],
) -> list[dict[str, float | str]]:
    thresholds = {
        "style_alignment_score": 0.12,
        "human_likeness_mean": 0.12,
        "unique_group_type_count": 0.5,
        "wordplay_group_count": 0.25,
        "theme_group_count": 0.2,
        "phonetic_group_count": 0.15,
        "surface_wordplay_score": 0.2,
        "surface_wordplay_group_count": 0.2,
        "formulaic_mix_score": 0.15,
        "family_saturation": 0.12,
        "family_repetition_risk": 0.12,
    }
    flags: list[dict[str, float | str]] = []
    for metric_name, threshold in sorted(thresholds.items()):
        generated_value = float(generated_metrics.get(metric_name, 0.0))
        benchmark_value = float(benchmark_metrics.get(metric_name, 0.0))
        delta = generated_value - benchmark_value
        if delta <= threshold:
            continue
        flags.append(
            {
                "metric_name": metric_name,
                "generated": round(generated_value, 4),
                "benchmark": round(benchmark_value, 4),
                "delta": round(delta, 4),
                "threshold": threshold,
            }
        )
    return flags


def _benchmark_anchor_warnings(
    style_metric_inflation_flags: list[dict[str, float | str]],
) -> list[str]:
    warnings: list[str] = []
    inflated_metric_names = {str(item["metric_name"]) for item in style_metric_inflation_flags}
    if "style_alignment_score" in inflated_metric_names:
        warnings.append(
            "Generated boards are outscoring the benchmark on style alignment; "
            "treat this as calibration inflation, not editorial success."
        )
    if {
        "unique_group_type_count",
        "wordplay_group_count",
        "theme_group_count",
    } & inflated_metric_names:
        warnings.append(
            "Generated boards still look too mixed relative to the benchmark holdout center."
        )
    if {
        "surface_wordplay_score",
        "surface_wordplay_group_count",
        "phonetic_group_count",
    } & inflated_metric_names:
        warnings.append(
            "Surface lexical and phonetic mechanisms are still overrepresented "
            "relative to the benchmark."
        )
    if {
        "formulaic_mix_score",
        "family_saturation",
        "family_repetition_risk",
    } & inflated_metric_names:
        warnings.append(
            "Formulaic-family inflation remains visible in generated boards and "
            "should continue to be penalized upstream."
        )
    return warnings


def run_quality_audit(
    *,
    run_dir: Path,
    normalized_dir: Path,
    reports_dir: Path,
) -> QualityAuditReport:
    """Compare generated top-k artifacts against the normalized public benchmark."""

    reports_dir.mkdir(parents=True, exist_ok=True)
    boards = load_normalized_benchmark(normalized_dir)
    manifest = BenchmarkManifest.model_validate(
        _read_json(normalized_dir / "benchmark_manifest.json")
    )
    calibration_split = _load_split(normalized_dir, "calibration_split.json")
    holdout_split = _load_split(normalized_dir, "holdout_split.json")
    freshness_split = _load_split(normalized_dir, "freshness_split.json")

    (
        generated_summary_payload,
        top_k_summary,
        accepted_records,
        _rejected_records,
        candidate_pool,
    ) = _load_generated_run(run_dir)
    generated_top_k_records = _top_k_records(accepted_records, top_k_summary, candidate_pool)
    benchmark_calibration_records = _slice_records_by_ids(boards, calibration_split)
    benchmark_holdout_records = _slice_records_by_ids(boards, holdout_split)
    benchmark_freshness_records = _slice_records_by_ids(boards, freshness_split)

    generated_slice_summary = build_batch_slice_summary(
        generated_top_k_records,
        slice_name="generated_top_k",
    )
    benchmark_holdout_summary = build_batch_slice_summary(
        benchmark_holdout_records,
        slice_name="benchmark_holdout",
    )
    benchmark_calibration_summary = build_batch_slice_summary(
        benchmark_calibration_records,
        slice_name="benchmark_calibration",
    )
    benchmark_freshness_summary = (
        build_batch_slice_summary(benchmark_freshness_records, slice_name="benchmark_freshness")
        if benchmark_freshness_records
        else None
    )

    generated_decisions = [record.verification_decision for record in generated_top_k_records]
    benchmark_decisions = [record.verification_decision for record in benchmark_holdout_records]
    generated_decision_counts = dict(
        sorted(Counter(decision or "unknown" for decision in generated_decisions).items())
    )
    benchmark_decision_counts = dict(
        sorted(Counter(decision or "unknown" for decision in benchmark_decisions).items())
    )
    generated_mechanism_shares = _counts_to_shares(generated_slice_summary.mechanism_mix_counts)
    benchmark_mechanism_shares = _counts_to_shares(benchmark_holdout_summary.mechanism_mix_counts)
    generated_score_summary = _score_summary(generated_top_k_records)
    benchmark_score_summary = _score_summary(benchmark_holdout_records)
    generated_anchor_metrics = _benchmark_anchor_metric_summary(
        generated_slice_summary,
        generated_score_summary,
    )
    benchmark_anchor_metrics = _benchmark_anchor_metric_summary(
        benchmark_holdout_summary,
        benchmark_score_summary,
    )
    style_metric_inflation_flags = _style_metric_inflation_flags(
        generated_anchor_metrics,
        benchmark_anchor_metrics,
    )
    benchmark_anchor_warnings = _benchmark_anchor_warnings(style_metric_inflation_flags)

    comparison_sections = {
        "verification_decision_distribution": {
            "generated_counts": generated_decision_counts,
            "benchmark_counts": benchmark_decision_counts,
            "generated_shares": _counts_to_shares(generated_decision_counts),
            "benchmark_shares": _counts_to_shares(benchmark_decision_counts),
            "l1_distance": _l1_distance(
                _counts_to_shares(generated_decision_counts),
                _counts_to_shares(benchmark_decision_counts),
            ),
        },
        "score_distribution_summary": _comparison_deltas(
            generated_score_summary,
            benchmark_score_summary,
        ),
        "mechanism_mix_distribution": {
            "generated_counts": generated_slice_summary.mechanism_mix_counts,
            "benchmark_counts": benchmark_holdout_summary.mechanism_mix_counts,
            "generated_shares": generated_mechanism_shares,
            "benchmark_shares": benchmark_mechanism_shares,
            "l1_distance": _l1_distance(generated_mechanism_shares, benchmark_mechanism_shares),
        },
        "style_distance_summary": _comparison_deltas(
            {
                **generated_slice_summary.style_metric_averages,
                **generated_slice_summary.label_shape_summary,
                **generated_slice_summary.board_diversity_summary,
            },
            {
                **benchmark_holdout_summary.style_metric_averages,
                **benchmark_holdout_summary.label_shape_summary,
                **benchmark_holdout_summary.board_diversity_summary,
            },
        ),
        "label_shape_summary": _comparison_deltas(
            generated_slice_summary.label_shape_summary,
            benchmark_holdout_summary.label_shape_summary,
        ),
        "board_diversity_summary": _comparison_deltas(
            generated_slice_summary.board_diversity_summary,
            benchmark_holdout_summary.board_diversity_summary,
        ),
        "ambiguity_summary": _comparison_deltas(
            _ambiguity_summary(generated_top_k_records),
            _ambiguity_summary(benchmark_holdout_records),
        ),
        "generated_vs_benchmark_style_delta_summary": _comparison_deltas(
            generated_anchor_metrics,
            benchmark_anchor_metrics,
        ),
        "style_metric_inflation_flags": style_metric_inflation_flags,
        "benchmark_anchor_warnings": benchmark_anchor_warnings,
    }

    generated_quality_buckets = _quality_bucket_counts(generated_decisions)
    benchmark_quality_buckets = _quality_bucket_counts(benchmark_decisions)
    machine_publishable_proxy = round(
        (
            generated_quality_buckets["accepted_high_confidence"]
            / max(len(generated_top_k_records), 1)
        ),
        4,
    )

    benchmark_summary_payload = {
        "manifest": manifest.model_dump(mode="json"),
        "calibration_split": {
            "count": calibration_split.count if calibration_split is not None else 0,
            "board_ids": calibration_split.board_ids if calibration_split is not None else [],
            "summary": benchmark_calibration_summary.model_dump(mode="json"),
        },
        "holdout_split": {
            "count": holdout_split.count if holdout_split is not None else 0,
            "board_ids": holdout_split.board_ids if holdout_split is not None else [],
            "summary": benchmark_holdout_summary.model_dump(mode="json"),
        },
        "freshness_split": (
            {
                "count": freshness_split.count,
                "board_ids": freshness_split.board_ids,
                "summary": benchmark_freshness_summary.model_dump(mode="json")
                if benchmark_freshness_summary is not None
                else None,
            }
            if freshness_split is not None
            else None
        ),
    }
    comparison_payload = {
        "generated_run_id": generated_summary_payload["run_id"],
        "generated_top_k_count": len(generated_top_k_records),
        "benchmark_holdout_count": len(benchmark_holdout_records),
        "generated_quality_buckets": generated_quality_buckets,
        "benchmark_quality_buckets": benchmark_quality_buckets,
        "comparison_sections": comparison_sections,
    }

    report = QualityAuditReport(
        generated_run_id=str(generated_summary_payload["run_id"]),
        generated_top_k_count=len(generated_top_k_records),
        benchmark_calibration_count=len(benchmark_calibration_records),
        benchmark_holdout_count=len(benchmark_holdout_records),
        split_policy=manifest.split_policy,
        generated_quality_buckets=generated_quality_buckets,
        benchmark_quality_buckets=benchmark_quality_buckets,
        comparison_sections=comparison_sections,
        quality_gate_summary={
            "machine_publishable_proxy": {
                "rate": machine_publishable_proxy,
                "definition": "Share of generated top-k boards with verifier decision 'accept'.",
                "not_human_gate": True,
            },
            "default_human_gate": {
                "threshold_rate": 0.4,
                "definition": (
                    "At least 40% of reviewed generated boards are publishable by majority vote."
                ),
                "human_rating_required": True,
            },
        },
        notes=[
            (
                "Benchmark-side verifier and scorer outputs use an "
                "answer-aware local solver for audit only."
            ),
            "Mechanism proportions on the benchmark are based on conservative heuristic labeling.",
            (
                "Automatic audit supports review prioritization but does "
                "not satisfy the final publishable-rate claim."
            ),
        ],
    )

    _write_json(reports_dir / "nyt_benchmark_summary.json", benchmark_summary_payload)
    _write_json(reports_dir / "generated_vs_nyt_comparison.json", comparison_payload)
    _write_json(reports_dir / "quality_audit_report.json", report.model_dump(mode="json"))
    (reports_dir / "quality_audit_report.md").write_text(
        _quality_audit_markdown(report, comparison_payload),
        encoding="utf-8",
    )
    return report


def _quality_audit_markdown(report: QualityAuditReport, comparison_payload: dict[str, Any]) -> str:
    lines = [
        "# NYT Benchmark Quality Audit",
        "",
        f"- Generated run: `{report.generated_run_id}`",
        f"- Generated top-k boards reviewed automatically: {report.generated_top_k_count}",
        f"- Benchmark holdout boards reviewed automatically: {report.benchmark_holdout_count}",
        f"- Split policy: {report.split_policy}",
        "",
        "## Machine Summary",
        (
            f"- Generated high-confidence top-k rate: "
            f"{report.quality_gate_summary['machine_publishable_proxy']['rate']:.3f}"
        ),
        (
            f"- Generated top-k quality buckets: "
            f"{json.dumps(report.generated_quality_buckets, sort_keys=True)}"
        ),
        (
            f"- Benchmark holdout quality buckets under current policy: "
            f"{json.dumps(report.benchmark_quality_buckets, sort_keys=True)}"
        ),
        "",
        "## Comparison Highlights",
        (
            f"- Verifier decision L1 distance: "
            f"{comparison_payload['comparison_sections']['verification_decision_distribution']['l1_distance']:.4f}"
        ),
        (
            f"- Mechanism mix L1 distance: "
            f"{comparison_payload['comparison_sections']['mechanism_mix_distribution']['l1_distance']:.4f}"
        ),
        (
            f"- Style inflation flags: "
            f"{len(comparison_payload['comparison_sections']['style_metric_inflation_flags'])}"
        ),
        (
            f"- Benchmark-anchor warnings: "
            f"{len(comparison_payload['comparison_sections']['benchmark_anchor_warnings'])}"
        ),
        "- Human blind review is still required for the final 40% publishable gate.",
    ]
    warnings = comparison_payload["comparison_sections"].get("benchmark_anchor_warnings", [])
    if warnings:
        lines.extend(["", "## Benchmark Anchor Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"
