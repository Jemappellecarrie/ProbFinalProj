import { useState } from "react";
import { DebugPanel } from "../components/DebugPanel";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PuzzleBoard } from "../components/PuzzleBoard";
import { RevealPanel } from "../components/RevealPanel";
import { ScorePanel } from "../components/ScorePanel";
import { usePuzzleGenerator } from "../hooks/usePuzzleGenerator";
import type { GroupType } from "../types/puzzle";

const DEFAULT_GROUP_TYPES: GroupType[] = ["semantic", "lexical", "phonetic", "theme"];

export function HomePage() {
  const { data, error, loading, loadSample, generate } = usePuzzleGenerator();
  const [revealed, setRevealed] = useState<boolean>(false);
  const [developerMode, setDeveloperMode] = useState<boolean>(true);

  async function handleGenerate() {
    setRevealed(false);
    await generate({
      include_trace: developerMode,
      developer_mode: developerMode,
      requested_group_types: DEFAULT_GROUP_TYPES,
      seed: Date.now(),
    });
  }

  async function handleLoadSample() {
    setRevealed(false);
    await loadSample();
  }

  return (
    <main className="page-shell">
      <section className="hero panel">
        <p className="eyebrow">Connections Generator</p>
        <h1>Production-style scaffold with an honest demo mode</h1>
        <p className="hero-copy">
          This UI is intentionally transparent: it runs a complete mock/baseline pipeline,
          surfaces score and trace metadata, and leaves the puzzle-defining quality logic
          explicitly human-owned.
        </p>
        <div className="control-row">
          <button className="primary-button" onClick={handleGenerate} disabled={loading}>
            Generate Puzzle
          </button>
          <button className="secondary-button" onClick={handleLoadSample} disabled={loading}>
            Load Static Sample
          </button>
          <button
            className="secondary-button"
            onClick={() => setRevealed((value) => !value)}
            disabled={!data}
          >
            {revealed ? "Hide Answers" : "Reveal Answers"}
          </button>
        </div>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={developerMode}
            onChange={(event) => setDeveloperMode(event.target.checked)}
          />
          <span>Developer mode</span>
        </label>
      </section>

      {loading && <LoadingState />}
      {error && !loading && <ErrorState message={error} onRetry={handleLoadSample} />}

      {data && !loading && (
        <div className="layout-grid">
          <PuzzleBoard boardWords={data.puzzle.board_words} groups={data.puzzle.groups} revealed={revealed} />
          <RevealPanel groups={data.puzzle.groups} revealed={revealed} />
          <ScorePanel score={data.score} verification={data.verification} />
          <DebugPanel response={data} visible={developerMode} />
        </div>
      )}
    </main>
  );
}
