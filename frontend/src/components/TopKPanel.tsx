import type { DebugComparisonView } from "../types/puzzle";

interface TopKPanelProps {
  comparison: DebugComparisonView | null;
}

export function TopKPanel({ comparison }: TopKPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Top-K Debug</p>
          <h2>Latest batch-evaluation ranking</h2>
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
              {comparison.summary.total_generated} puzzles.
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
                  <span className="pill">Score {record.score_breakdown.overall.toFixed(3)}</span>
                </div>
                <p className="muted">
                  Ambiguity risk: {record.ambiguity_risk_level ?? "unknown"} | Solver agreement:{" "}
                  {record.solver_agreement_ratio?.toFixed(3) ?? "n/a"} | Archetype:{" "}
                  {record.style_archetype ?? "n/a"}
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
