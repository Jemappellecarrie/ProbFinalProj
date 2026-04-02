import type { PuzzleScore, VerificationResult } from "../types/puzzle";

interface ScorePanelProps {
  score: PuzzleScore;
  verification: VerificationResult;
}

function formatFlags(flags: string[]) {
  return flags.length > 0 ? flags.join(", ") : "none";
}

function decisionClass(decision: string) {
  if (decision === "accept") {
    return "passed";
  }
  if (decision === "reject") {
    return "failed";
  }
  return "";
}

export function ScorePanel({ score, verification }: ScorePanelProps) {
  const boardStyleSummary = score.style_analysis?.board_style_summary;
  const mechanismMix = score.style_analysis?.mechanism_mix_profile?.counts ?? {};

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Scoring</p>
          <h2>Stage 1 score and Stage 3 style diagnostics</h2>
        </div>
        <span className={`pill ${decisionClass(verification.decision)}`}>
          {verification.decision.toUpperCase()}
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
          <span>Style alignment</span>
          <strong>{boardStyleSummary?.style_alignment_score?.toFixed(3) ?? "n/a"}</strong>
        </div>
      </div>
      <div className="subsection">
        <h3>Decision summary</h3>
        <ul className="simple-list">
          <li>
            <span>Verifier decision</span>
            <strong>{verification.decision}</strong>
          </li>
          <li>
            <span>Leakage estimate</span>
            <strong>{verification.leakage_estimate.toFixed(3)}</strong>
          </li>
          <li>
            <span>Warning flags</span>
            <strong>{formatFlags(verification.warning_flags)}</strong>
          </li>
          <li>
            <span>Style archetype</span>
            <strong>{score.style_analysis?.archetype.label ?? "n/a"}</strong>
          </li>
          <li>
            <span>Mechanism mix</span>
            <strong>
              {Object.keys(mechanismMix).length > 0
                ? Object.entries(mechanismMix)
                    .map(([label, count]) => `${label}:${count}`)
                    .join(", ")
                : "n/a"}
            </strong>
          </li>
        </ul>
      </div>
      <div className="subsection">
        <h3>Score components</h3>
        <ul className="simple-list">
          {Object.entries(score.components)
            .sort((left, right) => right[1] - left[1])
            .map(([label, value]) => (
              <li key={label}>
                <span>{label}</span>
                <strong>{value.toFixed(3)}</strong>
              </li>
            ))}
        </ul>
      </div>
      {score.style_analysis ? (
        <div className="subsection">
          <h3>Style analysis</h3>
          <p className="muted">
            Archetype: <strong>{score.style_analysis.archetype.label}</strong> | Board archetype:{" "}
            <strong>{boardStyleSummary?.board_archetype ?? "n/a"}</strong> | Placeholder
            NYT-likeness:{" "}
            <strong>{score.style_analysis.nyt_likeness.score?.toFixed(3) ?? "n/a"}</strong>
          </p>
          <ul className="simple-list">
            <li>
              <span>Out-of-band flags</span>
              <strong>{formatFlags(score.style_analysis.out_of_band_flags)}</strong>
            </li>
            <li>
              <span>Monotony score</span>
              <strong>{boardStyleSummary?.monotony_score?.toFixed(3) ?? "n/a"}</strong>
            </li>
            <li>
              <span>Evidence interpretability</span>
              <strong>{boardStyleSummary?.evidence_interpretability?.toFixed(3) ?? "n/a"}</strong>
            </li>
          </ul>
        </div>
      ) : null}
    </section>
  );
}
