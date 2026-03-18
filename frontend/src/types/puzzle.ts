export type GroupType = "semantic" | "lexical" | "phonetic" | "theme";

export interface GroupCandidate {
  candidate_id: string;
  group_type: GroupType;
  label: string;
  rationale: string;
  words: string[];
  word_ids: string[];
  source_strategy: string;
  extraction_mode: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface PuzzleCandidate {
  puzzle_id: string;
  board_words: string[];
  groups: GroupCandidate[];
  compatibility_notes: string[];
  metadata: Record<string, unknown>;
}

export interface VerificationResult {
  passed: boolean;
  reject_reasons: Array<{
    code: string;
    message: string;
    severity: string;
    metadata: Record<string, unknown>;
  }>;
  leakage_estimate: number;
  ambiguity_score: number;
  ambiguity_report: AmbiguityReport | null;
  ensemble_result: EnsembleSolverResult | null;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface PuzzleScore {
  scorer_name: string;
  overall: number;
  coherence: number;
  ambiguity_penalty: number;
  human_likeness: number | null;
  style_analysis: StyleAnalysisReport | null;
  components: Record<string, number>;
  notes: string[];
}

export interface TraceEvent {
  stage: string;
  message: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface GenerationTrace {
  trace_id: string;
  request_id: string;
  mode: string;
  feature_extractor: string;
  generators: string[];
  solver_backend: string;
  scorer: string;
  events: TraceEvent[];
  ensemble_result: EnsembleSolverResult | null;
  ambiguity_report: AmbiguityReport | null;
  style_analysis: StyleAnalysisReport | null;
  metadata: Record<string, unknown>;
}

export interface GeneratedPuzzleResponse {
  demo_mode: boolean;
  selected_components: Record<string, string | string[]>;
  warnings: string[];
  puzzle: PuzzleCandidate;
  verification: VerificationResult;
  score: PuzzleScore;
  trace: GenerationTrace | null;
}

export interface GroupTypeMetadata {
  type: GroupType;
  display_name: string;
  description: string;
}

export interface PuzzleGenerationRequest {
  seed?: number | null;
  include_trace: boolean;
  developer_mode: boolean;
  requested_group_types: GroupType[];
}

export interface WordGroupLeakage {
  word: string;
  word_id: string | null;
  source_group_label: string;
  target_group_label: string;
  leakage_kind: string;
  evidence_strength: number;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface CrossGroupCompatibility {
  left_group_label: string;
  right_group_label: string;
  compatibility_kind: string;
  shared_signals: string[];
  risk_weight: number;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface AlternativeGroupingCandidate {
  candidate_id: string;
  source_solver: string;
  proposed_groups: string[][];
  matched_target_solution: boolean;
  overlap_ratio: number;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface AmbiguityEvidence {
  word_group_leakage: WordGroupLeakage[];
  cross_group_compatibility: CrossGroupCompatibility[];
  alternative_groupings: AlternativeGroupingCandidate[];
  triggered_flags: string[];
  notes: string[];
}

export interface AmbiguityReport {
  evaluator_name: string;
  risk_level: string;
  penalty_hint: number;
  reject_recommended: boolean;
  summary: string;
  evidence: AmbiguityEvidence;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface SolverVote {
  solver_name: string;
  matched_target_solution: boolean;
  alternative_solution_proposed: boolean;
  solved: boolean;
  confidence: number | null;
  proposed_groups: string[][];
  notes: string[];
  raw_output: Record<string, unknown>;
}

export interface SolverAgreementSummary {
  total_solvers: number;
  matched_target_count: number;
  alternative_solution_count: number;
  agreement_ratio: number;
  disagreement_flags: string[];
  notes: string[];
}

export interface EnsembleSolverResult {
  coordinator_name: string;
  primary_solver_name: string | null;
  votes: SolverVote[];
  agreement_summary: SolverAgreementSummary;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface StyleSignal {
  signal_name: string;
  value: number;
  interpretation: string;
  source: string;
  metadata: Record<string, unknown>;
}

export interface PuzzleArchetypeSummary {
  label: string;
  rationale: string;
  flags: string[];
}

export interface NYTLikenessPlaceholderScore {
  score: number | null;
  notes: string[];
}

export interface StyleAnalysisReport {
  analyzer_name: string;
  archetype: PuzzleArchetypeSummary;
  nyt_likeness: NYTLikenessPlaceholderScore;
  signals: StyleSignal[];
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface ScoreBreakdownView {
  overall: number;
  coherence: number;
  ambiguity_penalty: number;
  human_likeness: number | null;
  components: Record<string, number>;
}

export interface RankedPuzzleRecord {
  rank: number;
  puzzle_id: string;
  accepted: boolean;
  board_words: string[];
  group_labels: string[];
  group_types: string[];
  score_breakdown: ScoreBreakdownView;
  ambiguity_risk_level: string | null;
  ambiguity_penalty_hint: number;
  solver_agreement_ratio: number | null;
  solver_disagreement_flags: string[];
  style_archetype: string | null;
  nyt_likeness_placeholder: number | null;
  trace_id: string | null;
  reject_risk_flags: string[];
  notes: string[];
}

export interface TopKSummary {
  requested_k: number;
  returned_count: number;
  ranked_puzzles: RankedPuzzleRecord[];
  notes: string[];
}

export interface BatchEvaluationSummary {
  run_id: string;
  created_at: string;
  total_generated: number;
  accepted_count: number;
  rejected_count: number;
  acceptance_rate: number;
  reject_reason_histogram: { counts: Record<string, number> };
  generator_mix: {
    group_type_counts: Record<string, number>;
    generator_strategy_counts: Record<string, number>;
  };
  score_distribution: {
    average_overall: number;
    average_coherence: number;
    average_ambiguity_penalty: number;
    average_human_likeness: number;
    min_overall: number;
    max_overall: number;
  };
  ambiguity_risk_distribution: Record<string, number>;
  solver_agreement_statistics: {
    total_ensemble_runs: number;
    unanimous_target_match_count: number;
    disagreement_count: number;
    average_agreement_ratio: number;
  };
  top_k: TopKSummary;
  output_dir: string;
  notes: string[];
}

export interface DebugComparisonView {
  run_id: string;
  summary: BatchEvaluationSummary;
  top_k: TopKSummary;
  notes: string[];
}

export interface LatestEvaluationDebugResponse {
  latest: DebugComparisonView | null;
}
