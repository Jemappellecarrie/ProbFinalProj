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

export interface SelectionSummary {
  selection_policy: string[];
  verification_decision: string;
  semantic_group_count: number;
  unique_group_type_count: number;
  mixed_board: boolean;
  mechanism_mix_summary: Record<string, number>;
  scorer_overall: number;
  ambiguity_penalty: number;
  style_alignment_score: number | null;
  composer_ranking_score: number;
  selection_reason: string;
  puzzle_id: string;
}

export interface PuzzleMetadata extends Record<string, unknown> {
  mixed_board?: boolean;
  mechanism_mix_summary?: Record<string, number>;
  unique_group_type_count?: number;
  ranking_score?: number;
  composition_trace?: {
    selection_summary?: SelectionSummary;
    [key: string]: unknown;
  };
}

export interface PuzzleCandidate {
  puzzle_id: string;
  board_words: string[];
  groups: GroupCandidate[];
  compatibility_notes: string[];
  metadata: PuzzleMetadata;
}

export interface RejectReason {
  code: string;
  message: string;
  severity: string;
  metadata: Record<string, unknown>;
}

export interface VerificationResult {
  passed: boolean;
  decision: string;
  reject_reasons: RejectReason[];
  warning_flags: string[];
  leakage_estimate: number;
  ambiguity_score: number;
  summary_metrics: Record<string, number>;
  evidence_refs: string[];
  ambiguity_report: AmbiguityReport | null;
  ensemble_result: EnsembleSolverResult | null;
  style_analysis: StyleAnalysisReport | null;
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

export interface TraceMetadata extends Record<string, unknown> {
  selection_summary?: SelectionSummary;
  composition?: Record<string, unknown>;
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
  metadata: TraceMetadata;
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

export interface WordFitSummary {
  word: string;
  word_id: string | null;
  assigned_group_label: string;
  assigned_support: number;
  strongest_competing_group_label: string | null;
  strongest_competing_support: number;
  leakage_margin: number;
  severity: string;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface GroupCoherenceSummary {
  group_label: string;
  support_score: number;
  mean_pairwise_similarity: number;
  weakest_member_support: number;
  strongest_competing_fit: number;
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
  words: string[];
  word_ids: string[];
  proposed_groups: string[][];
  matched_target_solution: boolean;
  overlap_ratio: number;
  label_hint: string | null;
  coherence_score: number;
  shared_signal_score: number;
  source_group_count: number;
  suspicion_score: number;
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface BoardAmbiguitySummary {
  board_pressure: number;
  max_alternative_group_pressure: number;
  high_leakage_word_count: number;
  strongest_confusing_pair: string | null;
  severity: string;
  warning_flags: string[];
  metrics: Record<string, number>;
}

export interface AmbiguityEvidence {
  group_coherence_summaries: GroupCoherenceSummary[];
  word_fit_summaries: WordFitSummary[];
  word_group_leakage: WordGroupLeakage[];
  cross_group_compatibility: CrossGroupCompatibility[];
  alternative_groupings: AlternativeGroupingCandidate[];
  board_summary: BoardAmbiguitySummary | null;
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

export interface MechanismMixProfile {
  counts: Record<string, number>;
  shares: Record<string, number>;
  unique_group_type_count: number;
  semantic_group_count: number;
  lexical_group_count: number;
  phonetic_group_count: number;
  theme_group_count: number;
  wordplay_group_count: number;
  mixed_board: boolean;
}

export interface GroupStyleSummary {
  group_label: string;
  group_type: string;
  archetype: string;
  label_token_count: number;
  label_clarity: number;
  label_specificity: number;
  evidence_interpretability: number;
  wordplay_indicator: number;
  redundancy_flags: string[];
  novelty_flags: string[];
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface BoardStyleSummary {
  board_archetype: string;
  mechanism_mix_profile: MechanismMixProfile;
  group_archetypes: string[];
  label_token_mean: number;
  label_token_std: number;
  label_consistency: number;
  evidence_interpretability: number;
  semantic_wordplay_balance: number;
  archetype_diversity: number;
  redundancy_score: number;
  monotony_score: number;
  coherence_trickiness_balance: number;
  style_alignment_score: number;
  out_of_band_flags: string[];
  notes: string[];
  metrics: Record<string, number>;
}

export interface StyleMetricComparison {
  metric_name: string;
  actual_value: number;
  target_min: number | null;
  target_max: number | null;
  within_band: boolean;
  drift: string;
  explanation: string;
  metadata: Record<string, unknown>;
}

export interface StyleAnalysisReport {
  analyzer_name: string;
  archetype: PuzzleArchetypeSummary;
  nyt_likeness: NYTLikenessPlaceholderScore;
  signals: StyleSignal[];
  group_style_summaries: GroupStyleSummary[];
  board_style_summary: BoardStyleSummary | null;
  mechanism_mix_profile: MechanismMixProfile | null;
  style_target_comparison: StyleMetricComparison[];
  out_of_band_flags: string[];
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
  verification_decision: string | null;
  board_words: string[];
  group_labels: string[];
  group_types: string[];
  mechanism_mix_summary: Record<string, number>;
  mixed_board: boolean;
  score_breakdown: ScoreBreakdownView;
  ambiguity_risk_level: string | null;
  ambiguity_penalty_hint: number;
  solver_agreement_ratio: number | null;
  solver_disagreement_flags: string[];
  style_archetype: string | null;
  nyt_likeness_placeholder: number | null;
  style_alignment_score: number | null;
  style_out_of_band_flags: string[];
  ranking_influence_notes: string[];
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

export interface GeneratorMixSummary {
  group_type_counts: Record<string, number>;
  generator_strategy_counts: Record<string, number>;
  board_mix_counts: Record<string, number>;
  board_type_signature_counts: Record<string, number>;
}

export interface ScoreDistributionSummary {
  average_overall: number;
  average_coherence: number;
  average_ambiguity_penalty: number;
  average_human_likeness: number;
  min_overall: number;
  max_overall: number;
}

export interface SolverAgreementStatistics {
  total_ensemble_runs: number;
  unanimous_target_match_count: number;
  disagreement_count: number;
  average_agreement_ratio: number;
}

export interface ThresholdDiagnostic {
  code: string;
  severity: string;
  message: string;
  metric_name: string | null;
  actual_value: number | null;
  target_min: number | null;
  target_max: number | null;
  metadata: Record<string, unknown>;
}

export interface CalibrationSliceSummary {
  puzzle_count: number;
}

export interface CalibrationSummary {
  target_version: string;
  accepted: CalibrationSliceSummary;
  rejected: CalibrationSliceSummary;
  top_k: CalibrationSliceSummary;
  threshold_diagnostics: ThresholdDiagnostic[];
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
  generator_mix: GeneratorMixSummary;
  score_distribution: ScoreDistributionSummary;
  ambiguity_risk_distribution: Record<string, number>;
  solver_agreement_statistics: SolverAgreementStatistics;
  top_k: TopKSummary;
  calibration_summary: CalibrationSummary | null;
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
