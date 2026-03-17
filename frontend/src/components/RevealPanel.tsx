import type { GroupCandidate } from "../types/puzzle";

interface RevealPanelProps {
  groups: GroupCandidate[];
  revealed: boolean;
}

export function RevealPanel({ groups, revealed }: RevealPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Solutions</p>
          <h2>Group breakdown</h2>
        </div>
      </div>
      {!revealed ? (
        <p className="muted">Reveal the answers to inspect labels, rationale, and grouped words.</p>
      ) : (
        <div className="solution-list">
          {groups.map((group) => (
            <article key={group.candidate_id} className={`solution-card ${group.group_type}`}>
              <p className="solution-type">{group.group_type}</p>
              <h3>{group.label}</h3>
              <p>{group.rationale}</p>
              <div className="chip-row">
                {group.words.map((word) => (
                  <span key={word} className="chip">
                    {word}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
