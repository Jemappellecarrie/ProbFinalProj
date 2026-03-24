# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Duke University Spring 2026 course project for Probability & Machine Learning. Implements the "Intentional Overlap" pipeline from the paper "Making New Connections: LLMs as Puzzle Generators for The New York Times' Connections Word Game" (arXiv 2407.11240) to generate NYT Connections-style word puzzles.

## How to Run

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<key>
python generate_puzzle.py
```

Requires: Python 3.10+, OpenAI API key with billing enabled.

## Architecture

**`generate_puzzle.py`** — single-file pipeline, 5 LLM calls + embedding selection:

1. **Diversity seeding**: Pick 4 random words from dataset → GPT generates a short story for creative inspiration
2. **Root group**: Few-shot prompt (3 random puzzles from dataset) → 1 category name + 8 candidate words
3. **3 Follow-up groups**: Each picks an overlap word from a prior group (different meaning), generates a new category + 8 words. Overlap words are tracked to prevent reuse.
4. **Embedding selection**: MPNet (`all-mpnet-base-v2`) ranks all C(8,4)=70 four-word combinations by average pairwise cosine similarity → outputs 4 difficulty variants per group (Yellow=easiest, Purple=hardest)

Category styles constrained to: Synonyms/Slang, Wordplay, Fill-in-the-blank.

## Data

- **`NYT-Connections/ConnectionsFinalDataset.json`** — 652 historical NYT Connections puzzles (COLING 2025 dataset, CC-BY-4.0). Used for few-shot examples and seed words.

## Key Dependencies

- `openai` — GPT-4o-mini API (model configurable via `MODEL` constant)
- `sentence-transformers` — MPNet embeddings for difficulty calibration

## Reference

- `2407.11240v1.pdf` — source paper describing the Intentional Overlap and False Connection pipelines
