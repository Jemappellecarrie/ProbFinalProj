import type { DebugComparisonView, GeneratedPuzzleResponse } from "../types/puzzle";

interface DebugPanelProps {
  response: GeneratedPuzzleResponse;
  comparison: DebugComparisonView | null;
  visible: boolean;
}

export function DebugPanel({ response, comparison, visible }: DebugPanelProps) {
  if (!visible) {
    return null;
  }

  return (
    <section className="panel debug-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Developer Mode</p>
          <h2>Debug trace and component wiring</h2>
        </div>
      </div>
      <div className="subsection">
        <h3>Selected components</h3>
        <pre>{JSON.stringify(response.selected_components, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Warnings</h3>
        <pre>{JSON.stringify(response.warnings, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Ambiguity Report</h3>
        <pre>{JSON.stringify(response.verification.ambiguity_report, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Solver Ensemble</h3>
        <pre>{JSON.stringify(response.verification.ensemble_result, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Style Analysis</h3>
        <pre>{JSON.stringify(response.score.style_analysis, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Latest Batch Comparison</h3>
        <pre>{JSON.stringify(comparison, null, 2)}</pre>
      </div>
      <div className="subsection">
        <h3>Trace</h3>
        <pre>{JSON.stringify(response.trace, null, 2)}</pre>
      </div>
    </section>
  );
}
