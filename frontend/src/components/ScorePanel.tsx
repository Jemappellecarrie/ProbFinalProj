import type { PuzzleScore, VerificationResult } from "../types/puzzle";

interface ScorePanelProps {
  score: PuzzleScore;
  verification: VerificationResult;
}

export function ScorePanel({ score, verification }: ScorePanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Scoring</p>
          <h2>Baseline score breakdown</h2>
        </div>
        <span className={`pill ${verification.passed ? "passed" : "failed"}`}>
          {verification.passed ? "Passed verification" : "Failed verification"}
        </span>
      </div>
      <div className="score-grid">
        <div className="score-card">
          <span>Overall</span>
          <strong>{score.overall.toFixed(3)}</strong>
        </div>
        <div className="score-card">
          <span>Coherence</span>
          <strong>{score.coherence.toFixed(3)}</strong>
        </div>
        <div className="score-card">
          <span>Ambiguity penalty</span>
          <strong>{score.ambiguity_penalty.toFixed(3)}</strong>
        </div>
        <div className="score-card">
          <span>Leakage estimate</span>
          <strong>{verification.leakage_estimate.toFixed(3)}</strong>
        </div>
      </div>
      <div className="subsection">
        <h3>Component values</h3>
        <ul className="simple-list">
          {Object.entries(score.components).map(([label, value]) => (
            <li key={label}>
              <span>{label}</span>
              <strong>{value.toFixed(3)}</strong>
            </li>
          ))}
        </ul>
      </div>
      {score.style_analysis ? (
        <div className="subsection">
          <h3>Style scaffold</h3>
          <p className="muted">
            Archetype: <strong>{score.style_analysis.archetype.label}</strong> | Placeholder
            NYT-likeness: <strong>{score.style_analysis.nyt_likeness.score?.toFixed(3) ?? "n/a"}</strong>
          </p>
          <ul className="simple-list">
            {score.style_analysis.signals.map((signal) => (
              <li key={signal.signal_name}>
                <span>{signal.signal_name}</span>
                <strong>{signal.value.toFixed(3)}</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
