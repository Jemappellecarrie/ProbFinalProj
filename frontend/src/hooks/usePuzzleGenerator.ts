import { useEffect, useState, startTransition } from "react";
import { generatePuzzle, getSamplePuzzle } from "../api/client";
import type { GeneratedPuzzleResponse, PuzzleGenerationRequest } from "../types/puzzle";

export function usePuzzleGenerator() {
  const [data, setData] = useState<GeneratedPuzzleResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadInitialPuzzle() {
      try {
        const payload = await getSamplePuzzle();
        if (!active) {
          return;
        }
        startTransition(() => {
          setData(payload);
          setError(null);
          setLoading(false);
        });
      } catch (caught) {
        if (!active) {
          return;
        }
        const message = caught instanceof Error ? caught.message : "Unknown error";
        setError(message);
        setLoading(false);
      }
    }

    void loadInitialPuzzle();
    return () => {
      active = false;
    };
  }, []);

  async function loadSample() {
    setLoading(true);
    try {
      const payload = await getSamplePuzzle();
      startTransition(() => {
        setData(payload);
        setError(null);
        setLoading(false);
      });
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unknown error";
      setError(message);
      setLoading(false);
    }
  }

  async function generate(request: PuzzleGenerationRequest) {
    setLoading(true);
    try {
      const payload = await generatePuzzle(request);
      startTransition(() => {
        setData(payload);
        setError(null);
        setLoading(false);
      });
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unknown error";
      setError(message);
      setLoading(false);
    }
  }

  return {
    data,
    loading,
    error,
    loadSample,
    generate,
  };
}
