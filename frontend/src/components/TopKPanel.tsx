import type { DebugComparisonView } from "../types/puzzle";

interface TopKPanelProps {
  comparison: DebugComparisonView | null;
}

function formatMix(mix: Record<string, number>) {
  return Object.entries(mix)
    .map(([label, count]) => `${label}:${count}`)
    .join(", ");
}

function formatFlags(flags: string[]) {
  return flags.length > 0 ? flags.join(", ") : "none";
}

export function TopKPanel({ comparison }: TopKPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Batch Eval</p>
          <h2>Latest ranking and calibration snapshot</h2>
        </div>
      </div>
      {!comparison ? (
        <p className="muted">
          No persisted batch evaluation was found yet. Run the batch CLI to populate this panel.
        </p>
      ) : (
        <>
          <div className="subsection">
            <p className="muted">
              Run <strong>{comparison.run_id}</strong> accepted {comparison.summary.accepted_count} of{" "}
              {comparison.summary.total_generated} puzzles. Calibration target:{" "}
              <strong>{comparison.summary.calibration_summary?.target_version ?? "n/a"}</strong>.
            </p>
          </div>
          <div className="solution-list">
            {comparison.top_k.ranked_puzzles.map((record) => (
              <article key={record.puzzle_id} className="solution-card">
                <div className="panel-header">
                  <div>
                    <p className="solution-type">Rank {record.rank}</p>
                    <h3>{record.group_labels.join(" / ")}</h3>
                  </div>
                  <span className="pill">
                    {record.verification_decision ?? "unknown"} | {record.score_breakdown.overall.toFixed(3)}
                  </span>
                </div>
                <p className="muted">
                  Mix: {formatMix(record.mechanism_mix_summary)} | Ambiguity risk:{" "}
                  {record.ambiguity_risk_level ?? "unknown"} | Solver agreement:{" "}
                  {record.solver_agreement_ratio?.toFixed(3) ?? "n/a"}
                </p>
                <p className="muted">
                  Style archetype: {record.style_archetype ?? "n/a"} | Style alignment:{" "}
                  {record.style_alignment_score?.toFixed(3) ?? "n/a"} | Out-of-band flags:{" "}
                  {formatFlags(record.style_out_of_band_flags)}
                </p>
                <div className="chip-row">
                  {record.board_words.map((word) => (
                    <span key={`${record.puzzle_id}-${word}`} className="chip">
                      {word}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
