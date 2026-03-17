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
    </section>
  );
}
