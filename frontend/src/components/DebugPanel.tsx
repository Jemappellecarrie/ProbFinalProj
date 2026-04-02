import type {
  BoardStyleSummary,
  DebugComparisonView,
  GeneratedPuzzleResponse,
  SelectionSummary,
} from "../types/puzzle";

interface DebugPanelProps {
  response: GeneratedPuzzleResponse;
  comparison: DebugComparisonView | null;
  visible: boolean;
}

function formatFlags(flags: string[]) {
  return flags.length > 0 ? flags.join(", ") : "none";
}

function formatMix(mix: Record<string, number>) {
  return Object.keys(mix).length > 0
    ? Object.entries(mix)
        .map(([label, count]) => `${label}:${count}`)
        .join(", ")
    : "n/a";
}

export function DebugPanel({ response, comparison, visible }: DebugPanelProps) {
  if (!visible) {
    return null;
  }

  const selectionSummary =
    (response.trace?.metadata.selection_summary as SelectionSummary | undefined) ??
    response.puzzle.metadata.composition_trace?.selection_summary;
  const boardStyleSummary = response.score.style_analysis?.board_style_summary as
    | BoardStyleSummary
    | undefined
    | null;
  const batchDiagnostics =
    comparison?.summary.calibration_summary?.threshold_diagnostics?.length ?? 0;

  return (
    <section className="panel debug-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Developer Mode</p>
          <h2>Stage 3 debug trace and release signals</h2>
        </div>
      </div>
      <div className="subsection">
        <h3>Selection summary</h3>
        <ul className="simple-list">
          <li>
            <span>Verification decision</span>
            <strong>{selectionSummary?.verification_decision ?? response.verification.decision}</strong>
          </li>
          <li>
            <span>Mechanism mix</span>
            <strong>
              {formatMix(
                selectionSummary?.mechanism_mix_summary ??
                  response.puzzle.metadata.mechanism_mix_summary ??
                  {},
              )}
            </strong>
          </li>
          <li>
            <span>Mixed board</span>
            <strong>{String(selectionSummary?.mixed_board ?? response.puzzle.metadata.mixed_board ?? false)}</strong>
          </li>
          <li>
            <span>Style alignment</span>
            <strong>
              {selectionSummary?.style_alignment_score?.toFixed(3) ??
                boardStyleSummary?.style_alignment_score?.toFixed(3) ??
                "n/a"}
            </strong>
          </li>
          <li>
            <span>Selection reason</span>
            <strong>{selectionSummary?.selection_reason ?? "n/a"}</strong>
          </li>
        </ul>
      </div>
      <div className="subsection">
        <h3>Verifier and ambiguity</h3>
        <ul className="simple-list">
          <li>
            <span>Ambiguity risk</span>
            <strong>{response.verification.ambiguity_report?.risk_level ?? "unknown"}</strong>
          </li>
          <li>
            <span>Warning flags</span>
            <strong>{formatFlags(response.verification.warning_flags)}</strong>
          </li>
          <li>
            <span>Leakage estimate</span>
            <strong>{response.verification.leakage_estimate.toFixed(3)}</strong>
          </li>
          <li>
            <span>Alternative-group pressure</span>
            <strong>
              {response.verification.summary_metrics.max_alternative_group_pressure?.toFixed(3) ?? "n/a"}
            </strong>
          </li>
        </ul>
      </div>
      <div className="subsection">
        <h3>Style and calibration</h3>
        <ul className="simple-list">
          <li>
            <span>Board archetype</span>
            <strong>{boardStyleSummary?.board_archetype ?? "n/a"}</strong>
          </li>
          <li>
            <span>Out-of-band flags</span>
            <strong>{formatFlags(response.score.style_analysis?.out_of_band_flags ?? [])}</strong>
          </li>
          <li>
            <span>Calibration diagnostics</span>
            <strong>{batchDiagnostics}</strong>
          </li>
          <li>
            <span>Latest batch target</span>
            <strong>{comparison?.summary.calibration_summary?.target_version ?? "n/a"}</strong>
          </li>
        </ul>
      </div>
      <div className="subsection">
        <h3>Selected components</h3>
        <pre>{JSON.stringify(response.selected_components, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Raw trace payload</h3>
        <pre>{JSON.stringify(response.trace, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Raw batch comparison payload</h3>
        <pre>{JSON.stringify(comparison, null, 2)}</pre>
      </div>
    </section>
  );
}
