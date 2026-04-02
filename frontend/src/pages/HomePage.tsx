import { useEffect, useState } from "react";
import { getLatestEvaluationDebugView } from "../api/client";
import { DebugPanel } from "../components/DebugPanel";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PuzzleBoard } from "../components/PuzzleBoard";
import { RevealPanel } from "../components/RevealPanel";
import { ScorePanel } from "../components/ScorePanel";
import { TopKPanel } from "../components/TopKPanel";
import { usePuzzleGenerator } from "../hooks/usePuzzleGenerator";
import type { DebugComparisonView, GroupType } from "../types/puzzle";

const DEFAULT_GROUP_TYPES: GroupType[] = ["semantic", "lexical", "phonetic", "theme"];

export function HomePage() {
  const { data, error, loading, loadSample, generate } = usePuzzleGenerator();
  const [revealed, setRevealed] = useState<boolean>(false);
  const [developerMode, setDeveloperMode] = useState<boolean>(true);
  const [comparison, setComparison] = useState<DebugComparisonView | null>(null);

  useEffect(() => {
    let active = true;

    async function loadComparison() {
      try {
        const payload = await getLatestEvaluationDebugView();
        if (!active) {
          return;
        }
        setComparison(payload);
      } catch {
        if (!active) {
          return;
        }
        setComparison(null);
      }
    }

    void loadComparison();
    return () => {
      active = false;
    };
  }, []);

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
        <h1>Stage 3 puzzle generator with release-grade debug surfaces</h1>
        <p className="hero-copy">
          This UI stays honest about the current system: it can exercise the demo baseline or the
          mixed semantic, lexical, phonetic, and theme pipeline, and it surfaces Stage 1 verifier
          decisions, Stage 3 style analysis, calibration-aware batch outputs, and trace metadata
          for review.
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
          {developerMode ? <TopKPanel comparison={comparison} /> : null}
          <DebugPanel response={data} comparison={comparison} visible={developerMode} />
        </div>
      )}
    </main>
  );
}
