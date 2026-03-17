import type {
  GeneratedPuzzleResponse,
  GroupTypeMetadata,
  PuzzleGenerationRequest,
} from "../types/puzzle";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getSamplePuzzle(): Promise<GeneratedPuzzleResponse> {
  return requestJson<GeneratedPuzzleResponse>("/puzzles/sample");
}

export function generatePuzzle(
  payload: PuzzleGenerationRequest,
): Promise<GeneratedPuzzleResponse> {
  return requestJson<GeneratedPuzzleResponse>("/puzzles/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getGroupTypes(): Promise<GroupTypeMetadata[]> {
  return requestJson<GroupTypeMetadata[]>("/metadata/group-types");
}
