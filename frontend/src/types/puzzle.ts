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
  notes: string[];
  metadata: Record<string, unknown>;
}

export interface PuzzleScore {
  scorer_name: string;
  overall: number;
  coherence: number;
  ambiguity_penalty: number;
  human_likeness: number | null;
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
