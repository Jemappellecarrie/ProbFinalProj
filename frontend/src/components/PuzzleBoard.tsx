import type { GroupCandidate } from "../types/puzzle";

interface PuzzleBoardProps {
  boardWords: string[];
  groups: GroupCandidate[];
  revealed: boolean;
}

function classForWord(word: string, groups: GroupCandidate[], revealed: boolean): string {
  if (!revealed) {
    return "tile";
  }

  const match = groups.find((group) => group.words.includes(word));
  return `tile revealed ${match?.group_type ?? "unassigned"}`;
}

export function PuzzleBoard({ boardWords, groups, revealed }: PuzzleBoardProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Puzzle Board</p>
          <h2>Sixteen words, four hidden groups</h2>
        </div>
        <span className="pill">{revealed ? "Solution visible" : "Board mixed"}</span>
      </div>
      <div className="board-grid">
        {boardWords.map((word) => (
          <div key={word} className={classForWord(word, groups, revealed)}>
            {word}
          </div>
        ))}
      </div>
    </section>
  );
}
