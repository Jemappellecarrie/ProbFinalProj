"""
NYT Connections Puzzle Generator — Intentional Overlap Pipeline

Based on: "Making New Connections: LLMs as Puzzle Generators for
The New York Times' Connections Word Game" (arXiv 2407.11240)

Generates 4 word groups, each with a category name and 8 candidate words.
Follow-up groups intentionally share an ambiguous word with a prior group.
Then selects 4 words from each 8-word pool using MPNet embedding similarity
to calibrate difficulty (Yellow=easy → Purple=hard).
"""

import io
import itertools
import json
import os
import random
import re
import sys

# Fix Windows terminal encoding for special characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# --------------- Configuration ---------------

MODEL = "gpt-5.2"
TEMPERATURE = 1.0
NUM_FEWSHOT = 3
DATASET_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "NYT-Connections",
    "ConnectionsFinalDataset.json",
)

# --------------- Data Loading ---------------


def load_dataset(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_fewshot_examples(dataset: list[dict], n: int = NUM_FEWSHOT) -> list[dict]:
    return random.sample(dataset, min(n, len(dataset)))


def format_group(answer: dict) -> str:
    words = ", ".join(answer["words"])
    return f"  Category: {answer['answerDescription']}\n  Words: {words}"


def format_fewshot_examples(examples: list[dict]) -> str:
    parts = []
    for i, puzzle in enumerate(examples, 1):
        groups = "\n".join(
            f"  Group {j}: {format_group(ans).strip()}"
            for j, ans in enumerate(puzzle["answers"], 1)
        )
        parts.append(f"--- Example Puzzle {i} ---\n{groups}")
    return "\n\n".join(parts)


def pick_seed_words(dataset: list[dict], n: int = 4) -> list[str]:
    puzzles = random.sample(dataset, min(n, len(dataset)))
    return [random.choice(p["words"]) for p in puzzles]


# --------------- LLM Calls ---------------

def make_client() -> OpenAI:
    openai_token = os.getenv("OPENAI_API_KEY")
    if openai_token:
        return OpenAI(api_key=openai_token)

    litellm_token = os.getenv("LITELLM_TOKEN")
    if litellm_token:
        return OpenAI(
            api_key=litellm_token,
            base_url="https://litellm.oit.duke.edu/v1",
        )

    raise RuntimeError(
        "Neither OPENAI_API_KEY nor LITELLM_TOKEN is set."
    )

def call_gpt4(client: OpenAI, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content


def generate_diversity_story(client: OpenAI, seed_words: list[str]) -> str:
    words_str = ", ".join(seed_words)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a creative writer. Write a short, imaginative story "
                "(2-3 sentences) that naturally incorporates ALL of the following "
                f"words: {words_str}. The story should be vivid and touch on "
                "unexpected themes."
            ),
        },
        {
            "role": "user",
            "content": f"Write a short story using these words: {words_str}",
        },
    ]
    return call_gpt4(client, messages)


CATEGORY_STYLE_INSTRUCTIONS = """\
Category style MUST be one of these four types. Each type has labeled subcategories
(a), (b), (c), etc. You may choose ANY subcategory within a type.

IMPORTANT DISTRIBUTION RULE for a complete 4-group puzzle:
- Types 1 (Synonyms/Slang) and 4 (Knowledge-based) MUST appear in at least 2 of the 4 groups combined.
- Type 3 (Fill-in-the-blank) may appear in at most 1 of the 4 groups.
- Type 2 (Wordplay) may appear in 0-2 of the 4 groups.
The LLM is free to choose which specific type and subcategory to use for each group,
as long as the above distribution is respected.

1. Synonyms/Slang — All 4 words mean the same thing (or nearly the same thing),
   including informal slang, metaphors, and figurative language.
   (a) Direct synonyms: words that are standard synonyms
       "HAPPY" → GLAD, ELATED, THRILLED, STOKED
   (b) Slang/informal: words where some or all are slang for the same concept
       "MONEY" → CASH, DOUGH, BREAD, BUCKS
   (c) Figurative/metaphorical: words that are metaphors for the same idea
       "CONFORMISTS" → FOLLOWERS, LEMMINGS, PUPPETS, SHEEP

2. Wordplay — All 4 words share a hidden linguistic trick. The category name MUST
   explicitly state what the trick is.
   (a) Homophones: words that SOUND LIKE something else
       "PHILOSOPHER HOMOPHONES" → LOCK, MARKS, PANE, RUSTLE (sound like Locke, Marx, Paine, Russell)
       "SOUNDS LIKE A GREEK LETTER" → MOO, NEW, PIE, ROW (sound like Mu, Nu, Pi, Rho)
   (b) Hidden word: a secret word is hiding INSIDE each word's spelling
       "WORDS CONTAINING A FISH" → ABSTRACT, TROUPE, SHARPEN, COBALT (hide BASS, TROUT, SHARP, COBALT)
   (c) Anagram: letters can be rearranged to spell something in a shared category
       "ANAGRAMS OF FRUITS" → PALEG, MELNO, HCAEP, PLPAE (rearrange to GRAPE, LEMON, PEACH, APPLE)
   (d) Add/subtract letters: adding or removing letters from each word reveals a hidden category
       "REMOVE FIRST LETTER TO GET A NUMBER" → HEIGHT, LONE, CANINE, OFTEN (eight, one, nine, ten)
   (e) Palindrome: words that read the same forwards and backwards
       "PALINDROMES" → LEVEL, KAYAK, CIVIC, RADAR
   (f) Every letter is a Greek letter name: the word can be fully split into Greek letter names
       "SPELLED ENTIRELY WITH GREEK LETTERS" → ALPHA, ALPHABET, PIOUS, PHOENIX

3. Fill-in-the-blank — All 4 words complete the SAME phrase when placed in the blank.
   The category name must show the blank with "___".
   (a) Prefix blank: "___ X" where the blank comes before
       "___ HOUSE" → FIRE, GREEN, WARE, POWER
   (b) Suffix blank: "X ___" where the blank comes after
       "B-___" → BALL, MOVIE, SCHOOL, VITAMIN
   (c) Compound blank: words form a compound word or common phrase with the given word
       "___ CAMP" → BAND, BASE, BOOT, SUMMER

4. Knowledge-based — All 4 words belong to the same real-world category or appear in
   the same scenario. Ideally, some words also have a common DIFFERENT meaning that
   could mislead players.
   (a) Taxonomy: words that belong to a specific real-world class
       "FISH" → CHAR, POLLOCK, SOLE, TANG (all are fish, but also mean other things)
       "HONDA MODELS" → ACCORD, CIVIC, ODYSSEY, PILOT (all are Honda cars, but also common English words)
   (b) Scenario/setting: words that all appear together in a specific situation
       "GRADUATION" → TASSEL, GOWN, CAP, DIPLOMA
       "POKER TABLE" → CHIPS, FOLD, BLIND, RIVER
   (c) Pop culture: words tied to a specific cultural domain
       "TAYLOR SWIFT ALBUMS" → FOLKLORE, MIDNIGHTS, REPUTATION, LOVER"""

WORD_DIFFICULTY_INSTRUCTIONS = """\
WORD DIFFICULTY PREFERENCE:
- Prefer words that feel medium-to-hard for a human Connections solver.
- Avoid overly simple, first-thought, beginner-level words when a sharper option exists.
- Favor words with nuance, secondary meanings, or less obvious associations.
- Still keep the puzzle fair: use real, recognizable words, not ultra-obscure trivia.
- For knowledge-based groups, prefer entries that are recognizable but not the most obvious 4 examples.
- Do NOT make all 8 candidates extremely easy or overly literal.
- Do not make all four answers contain or begin with the same overlapping visible part.
- Do not make all four answers begin with the same visible token.
- Do not make all four answers contain the same conspicuous prefix, suffix, or repeated letter chunk."""


def generate_root_group(
    client: OpenAI, fewshot_text: str, story: str
) -> dict:
    system_prompt = f"""\
You are a puzzle designer for the New York Times "Connections" word game.
In this game, 16 words are arranged in a grid, and players must find 4 groups
of 4 words that share a hidden connection.

Your task: generate ONE group for a Connections puzzle. Provide a category name
and exactly 8 candidate words that fit that category.

{CATEGORY_STYLE_INSTRUCTIONS}
{WORD_DIFFICULTY_INSTRUCTIONS}

Here are examples of complete Connections puzzles for reference:

{fewshot_text}

Use the following short story as creative inspiration for your category theme.
Do NOT directly copy categories from the examples above.

Story: {story}

Respond in EXACTLY this format (words in ALL CAPS):
CATEGORY: <category name>
WORDS: <word1>, <word2>, <word3>, <word4>, <word5>, <word6>, <word7>, <word8>"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate one word group now."},
    ]
    text = call_gpt4(client, messages)
    return parse_group_response(text)


def _detect_style(category: str) -> str:
    """Detect which category style a group uses based on its category name."""
    cat = category.upper()
    if "___" in cat or "BLANK" in cat:
        return "Fill-in-the-blank"
    wordplay_keywords = ["HOMOPHONE", "ANAGRAM", "HIDDEN", "CONTAINING", "SOUNDS LIKE",
                         "RHYME", "SPELLED"]
    if any(kw in cat for kw in wordplay_keywords):
        return "Wordplay"
    knowledge_keywords = ["FISH", "PLANET", "GREEK", "LETTER", "ANIMAL", "FRUIT",
                          "COUNTRY", "CITY", "TEAM", "BRAND", "COLOR", "FLOWER",
                          "TREE", "BIRD", "ELEMENT", "RIVER", "MOUNTAIN", "CURRENCY"]
    if any(kw in cat for kw in knowledge_keywords):
        return "Knowledge-based"
    return "Synonyms/Slang"


def _build_style_constraint(prior_groups: list[dict]) -> str:
    """Count styles used so far and build a constraint if any style has 2+ uses."""
    style_counts = {}
    for g in prior_groups:
        style = _detect_style(g["category"])
        style_counts[style] = style_counts.get(style, 0) + 1

    maxed_styles = [s for s, c in style_counts.items() if c >= 2]
    if not maxed_styles:
        return ""

    style_list = ", ".join(maxed_styles)
    summary = ", ".join(f"{s}: {c}" for s, c in style_counts.items())
    return (
        f"\nSTYLE VARIETY CONSTRAINT:\n"
        f"The existing groups already use these styles: {summary}.\n"
        f"The following style(s) have been used 2 or more times and MUST NOT be used again: {style_list}.\n"
        f"You MUST pick a DIFFERENT category style for this group.\n"
    )


def generate_followup_group(
    client: OpenAI,
    fewshot_text: str,
    prior_groups: list[dict],
    group_number: int,
    used_overlap_words: list[str],
) -> dict:
    prior_text = "\n".join(
        f"  Group {i}: Category: {g['category']}\n"
        f"           Words: {', '.join(g['words'])}"
        for i, g in enumerate(prior_groups, 1)
    )

    # Build constraint about already-used overlap words
    if used_overlap_words:
        used_str = ", ".join(used_overlap_words)
        overlap_constraint = (
            f"\nCRITICAL CONSTRAINTS:\n"
            f"- The following words have ALREADY been used as overlap words and "
            f"MUST NOT be picked again: {used_str}\n"
            f"- You MUST pick a DIFFERENT word that has NOT been used as an overlap word yet.\n"
            f"- Try to pick from a DIFFERENT group than previous overlap words came from.\n"
        )
    else:
        overlap_constraint = ""

    # Build style variety constraint
    style_constraint = _build_style_constraint(prior_groups)

    system_prompt = f"""\
You are a puzzle designer for the New York Times "Connections" word game.

You are creating a puzzle using the "Intentional Overlap" method. You have already
generated the following group(s):

{prior_text}

Your task: create a NEW group that intentionally overlaps with a previous group.
Steps:
1. Pick ONE word from one of the existing groups above that has a clear SECOND meaning.
2. Think of a DIFFERENT meaning, association, or interpretation of that word.
   For example: WIND (breeze) vs WIND (to coil), SPRING (season) vs SPRING (to jump).
3. Design a new category around that alternate meaning.
4. Generate 8 candidate words for your new category. The picked word MUST be one of
   the 8 words (this creates the intentional overlap that makes the puzzle tricky).
5. Your new category MUST be thematically VERY DIFFERENT from all existing groups.
   Do NOT create a category that is a near-synonym or subset of an existing one.
{overlap_constraint}{style_constraint}
{CATEGORY_STYLE_INSTRUCTIONS}
{WORD_DIFFICULTY_INSTRUCTIONS}

Here are examples of real Connections puzzles for reference:

{fewshot_text}

This is group {group_number} of 4.

Respond in EXACTLY this format (words in ALL CAPS):
OVERLAP_WORD: <the word you picked from a prior group>
SOURCE_GROUP: <the category name of the group you picked it from>
CATEGORY: <your new category name>
WORDS: <word1>, <word2>, <word3>, <word4>, <word5>, <word6>, <word7>, <word8>"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate group {group_number} now."},
    ]
    text = call_gpt4(client, messages)
    return parse_followup_response(text)


# --------------- Parsing ---------------


def _extract_field(text: str, field: str) -> str | None:
    pattern = rf"^{field}\s*:\s*(.+)$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _parse_words(words_str: str) -> list[str]:
    return [w.strip().upper() for w in words_str.split(",") if w.strip()]


def parse_group_response(text: str) -> dict:
    category = _extract_field(text, "CATEGORY")
    words_str = _extract_field(text, "WORDS")

    if not category or not words_str:
        print(f"  [WARNING] Could not parse response. Raw output:\n{text}")
        return {"category": category or "UNKNOWN", "words": _parse_words(words_str or "")}

    words = _parse_words(words_str)
    if len(words) != 8:
        print(f"  [WARNING] Expected 8 words, got {len(words)}: {words}")

    return {"category": category, "words": words}


def parse_followup_response(text: str) -> dict:
    result = parse_group_response(text)
    result["overlap_word"] = _extract_field(text, "OVERLAP_WORD") or "?"
    result["source_group"] = _extract_field(text, "SOURCE_GROUP") or "?"
    return result


# --------------- Embedding-Based Word Selection ---------------

DIFFICULTY_COLORS = ["Yellow (Easiest)", "Green", "Blue", "Purple (Hardest)"]


def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer("all-mpnet-base-v2")


def avg_pairwise_cosine(embeddings: np.ndarray) -> float:
    """Average pairwise cosine similarity for a set of embeddings."""
    norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    sim_matrix = norms @ norms.T
    n = len(embeddings)
    # Sum upper triangle (excluding diagonal), divide by number of pairs
    total = np.sum(np.triu(sim_matrix, k=1))
    pairs = n * (n - 1) / 2
    return float(total / pairs)


def rank_combinations(words: list[str], model: SentenceTransformer) -> list[tuple]:
    """
    For an 8-word pool, compute embedding similarity for all C(8,4)=70
    combinations of 4 words. Return sorted list of (similarity, combo).
    """
    embeddings = model.encode(words)
    word_to_idx = {w: i for i, w in enumerate(words)}

    scored = []
    for combo in itertools.combinations(words, 4):
        idxs = [word_to_idx[w] for w in combo]
        sim = avg_pairwise_cosine(embeddings[idxs])
        scored.append((sim, list(combo)))

    scored.sort(key=lambda x: x[0], reverse=True)  # highest similarity first
    return scored


def select_difficulty_variants(
    words: list[str], model: SentenceTransformer
) -> dict[str, dict]:
    """
    Select 4 difficulty variants from an 8-word pool:
      Yellow (easiest): highest similarity combo
      Green:  combo at ~1/3 from top
      Blue:   combo at ~2/3 from top
      Purple (hardest): lowest similarity combo
    """
    ranked = rank_combinations(words, model)
    n = len(ranked)

    indices = {
        "Yellow (Easiest)": 0,
        "Green": n // 3,
        "Blue": 2 * n // 3,
        "Purple (Hardest)": n - 1,
    }

    return {
        color: {"words": ranked[idx][1], "similarity": round(ranked[idx][0], 4)}
        for color, idx in indices.items()
    }


# --------------- Puzzle Assembly & Validation ---------------


def find_overlaps(groups: list[dict]) -> dict[str, list[int]]:
    """Map each candidate word to the group indices whose pool contains it."""
    word_to_groups = {}
    for i, g in enumerate(groups):
        for w in g["words"]:
            word_to_groups.setdefault(w, []).append(i)
    return word_to_groups


def score_word_in_group(
    word_emb: np.ndarray, group_embs: np.ndarray
) -> float:
    """Average cosine similarity of a word embedding to a set of group embeddings."""
    w_norm = word_emb / np.linalg.norm(word_emb)
    g_norms = group_embs / np.linalg.norm(group_embs, axis=1, keepdims=True)
    return float(np.mean(g_norms @ w_norm))


def _difficulty_index(target: str, n: int) -> int:
    mapping = {
        "Yellow (Easiest)": 0,
        "Green": n // 3,
        "Blue": 2 * n // 3,
        "Purple (Hardest)": n - 1,
    }
    return mapping.get(target, 0)


def assemble_puzzle(
    groups: list[dict],
    model: SentenceTransformer,
    target_difficulty: str = "Yellow (Easiest)",
) -> dict | None:
    """
    Assemble a valid 16-word puzzle from 4 groups of 8 candidates.
    Tries all overlap assignments (2^k), picks the best valid one.
    During assembly, each group uses the same target difficulty so we favor
    semantically cohesive groups; final displayed difficulty is ranked later.
    """
    word_to_groups = find_overlaps(groups)
    overlap_words = {w: gidxs for w, gidxs in word_to_groups.items() if len(gidxs) > 1}

    # Pre-encode all unique words across all groups
    all_unique = list({w for g in groups for w in g["words"]})
    all_embs = model.encode(all_unique)
    emb_map = {w: all_embs[i] for i, w in enumerate(all_unique)}

    # Generate all possible overlap assignments
    if not overlap_words:
        assignment_options = [{}]
    else:
        overlap_items = list(overlap_words.items())
        choices = [[(w, gi) for gi in gidxs] for w, gidxs in overlap_items]
        assignment_options = [dict(combo) for combo in itertools.product(*choices)]

    # Score each assignment by semantic fit and try best first
    def score_assignment(assignment):
        total = 0.0
        for word, gi in assignment.items():
            others = [w for w in groups[gi]["words"] if w != word]
            if not others:
                continue
            other_embs = np.array([emb_map[w] for w in others])
            total += score_word_in_group(emb_map[word], other_embs)
        return total

    assignment_options.sort(key=score_assignment, reverse=True)

    best_result = None
    for assignment in assignment_options:
        result = _try_assignment(
            groups, assignment, word_to_groups, emb_map, model, target_difficulty
        )
        if result is None:
            continue
        if result["valid"]:
            return result
        # Keep track of best invalid result (fewest ambiguous words)
        if best_result is None or len(result["ambiguous_words"]) < len(
            best_result["ambiguous_words"]
        ):
            best_result = result

    return best_result  # may be None or best-effort invalid


def _try_assignment(
    groups: list[dict],
    assignment: dict[str, int],
    word_to_groups: dict[str, list[int]],
    emb_map: dict[str, np.ndarray],
    model: SentenceTransformer,
    target_difficulty: str,
) -> dict | None:
    """Given overlap assignments, build pools and select 4 words per group."""
    puzzle = []
    used_words = set()

    for gi, g in enumerate(groups):
        available = []
        for w in g["words"]:
            if w in assignment and assignment[w] != gi:
                continue  # overlap word assigned to another group
            if w in used_words:
                continue
            available.append(w)

        if len(available) < 4:
            return None

        ranked = rank_combinations(available, model)
        idx = _difficulty_index(target_difficulty, len(ranked))
        selected = ranked[idx][1]
        sim = ranked[idx][0]

        puzzle.append({
            "category": g["category"],
            "words": selected,
            "similarity": round(sim, 4),
        })
        used_words.update(selected)

    # Final check: 16 unique words
    all_words = [w for p in puzzle for w in p["words"]]
    if len(set(all_words)) != 16:
        return None

    validation = validate_unique_solution(puzzle, emb_map)
    return {
        "puzzle": puzzle,
        "valid": validation["valid"],
        "ambiguous_words": validation["ambiguous_words"],
        "difficulty_issues": validation["difficulty_issues"],
    }


def validate_unique_solution(
    puzzle: list[dict], emb_map: dict[str, np.ndarray]
) -> dict:
    """
    For each word, verify it's most similar to its own group-mates
    (avg cosine to own 3 group-mates > avg cosine to any other group's 4 words).
    """
    ambiguous = []

    for gi, p in enumerate(puzzle):
        for w in p["words"]:
            w_emb = emb_map[w]
            scores = {}

            for gj, q in enumerate(puzzle):
                others = [ow for ow in q["words"] if ow != w]
                if not others:
                    scores[gj] = 0.0
                    continue
                other_embs = np.array([emb_map[ow] for ow in others])
                scores[gj] = score_word_in_group(w_emb, other_embs)

            own_score = scores[gi]
            best_other_gj = max(
                (gj for gj in scores if gj != gi), key=lambda gj: scores[gj]
            )
            margin = own_score - scores[best_other_gj]

            if margin <= 0:
                ambiguous.append((
                    w,
                    puzzle[gi]["category"],
                    puzzle[best_other_gj]["category"],
                    round(margin, 4),
                ))

    difficulty_issues = find_surface_pattern_issues(puzzle)
    return {
        "valid": len(ambiguous) == 0 and len(difficulty_issues) == 0,
        "ambiguous_words": ambiguous,
        "difficulty_issues": difficulty_issues,
    }


def _normalize_surface_text(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def _word_tokens(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[A-Z]+", text.upper()) if tok]


def _longest_common_substring(words: list[str]) -> str:
    if not words:
        return ""

    shortest = min(words, key=len)
    best = ""
    for length in range(len(shortest), 2, -1):
        for start in range(len(shortest) - length + 1):
            candidate = shortest[start : start + length]
            if candidate in best:
                continue
            if all(candidate in word for word in words):
                return candidate
    return best


def find_surface_pattern_issues(puzzle: list[dict]) -> list[tuple[str, str, str]]:
    """
    Flag groups that are too easy because they share an overly obvious surface pattern,
    such as the same visible token across all entries or the same visible substring.
    """
    issues = []

    for group in puzzle:
        words = group["words"]
        token_sets = [set(_word_tokens(word)) for word in words]
        shared_tokens = set.intersection(*token_sets) if token_sets else set()
        meaningful_shared_tokens = [tok for tok in shared_tokens if len(tok) >= 4]
        if meaningful_shared_tokens:
            token = sorted(meaningful_shared_tokens, key=len, reverse=True)[0]
            issues.append((
                group["category"],
                "shared_token",
                token,
            ))
            continue

        normalized_words = [_normalize_surface_text(word) for word in words]
        shared_substring = _longest_common_substring(normalized_words)
        if len(shared_substring) >= 4:
            issues.append((
                group["category"],
                "shared_substring",
                shared_substring,
            ))
            continue

        if len(shared_substring) == 3:
            visible_boundary_match = all(
                word.startswith(shared_substring) or word.endswith(shared_substring)
                for word in normalized_words
            )
            if visible_boundary_match:
                issues.append((
                    group["category"],
                    "shared_substring",
                    shared_substring,
                ))

    return issues


# --------------- LLM Difficulty Ranking ---------------


def rank_difficulty_with_llm(client: OpenAI, puzzle: list[dict]) -> list[dict]:
    """
    Ask the LLM to rank 4 groups from easiest to hardest, then assign
    Yellow (easiest), Green, Blue, Purple (hardest) accordingly.
    Returns the puzzle list reordered by difficulty color.
    """
    groups_text = "\n".join(
        f"  Group {i+1}: Category: {g['category']}\n"
        f"           Words: {', '.join(g['words'])}"
        for i, g in enumerate(puzzle)
    )

    system_prompt = f"""\
You are an expert player of the New York Times "Connections" word game.

Given 4 word groups from a Connections puzzle, rank them from EASIEST to HARDEST
for a human player to identify. Consider:
- How obvious is the connection between the words?
- Are the words common or obscure?
- Does the category involve wordplay or hidden tricks (harder) vs simple synonyms (easier)?
- Could any words be easily confused with another group?

Here are the 4 groups:

{groups_text}

Respond in EXACTLY this format — list the group numbers from easiest to hardest:
EASIEST: <group number>
EASY: <group number>
HARD: <group number>
HARDEST: <group number>"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Rank these groups by difficulty now."},
    ]
    text = call_gpt4(client, messages)

    # Parse the ranking
    color_map = {
        "EASIEST": "Yellow (Easiest)",
        "EASY": "Green",
        "HARD": "Blue",
        "HARDEST": "Purple (Hardest)",
    }

    ranked_puzzle = []
    used_indices = set()
    for level, color in color_map.items():
        match = re.search(rf"{level}\s*:\s*(\d+)", text, re.IGNORECASE)
        if match:
            idx = int(match.group(1)) - 1  # convert to 0-based
            if 0 <= idx < len(puzzle) and idx not in used_indices:
                group = dict(puzzle[idx])
                group["color"] = color
                ranked_puzzle.append(group)
                used_indices.add(idx)

    # Fallback: if parsing failed, assign colors by embedding similarity
    if len(ranked_puzzle) != 4:
        print("  [WARNING] LLM difficulty ranking parse failed, falling back to embedding order.")
        sorted_by_sim = sorted(puzzle, key=lambda g: g["similarity"], reverse=True)
        colors = ["Yellow (Easiest)", "Green", "Blue", "Purple (Hardest)"]
        ranked_puzzle = []
        for i, g in enumerate(sorted_by_sim):
            group = dict(g)
            group["color"] = colors[i]
            ranked_puzzle.append(group)

    return ranked_puzzle


# --------------- Output ---------------


def print_header(seed_words: list[str], story: str):
    print("=" * 60)
    print("  NYT CONNECTIONS PUZZLE GENERATOR (Intentional Overlap)")
    print("=" * 60)
    print(f"\nSeed words: {', '.join(seed_words)}")
    print(f"Story: {story}\n")


def print_group(group: dict, number: int):
    print("-" * 60)
    if number == 1:
        label = "GROUP 1 (Root)"
    else:
        overlap = group.get("overlap_word", "?")
        source = group.get("source_group", "?")
        label = f'GROUP {number} (Overlap: "{overlap}" from {source})'
    print(label)
    print(f"  Category: {group['category']}")
    print(f"  Candidates ({len(group['words'])}): {', '.join(group['words'])}")


def print_results(groups: list[dict]):
    print("-" * 60)
    print("\n" + "=" * 60)
    print("  SUMMARY: All 4 Generated Groups")
    print("=" * 60)
    for i, g in enumerate(groups, 1):
        print(f"\n  [{i}] {g['category']}")
        print(f"      {', '.join(g['words'])}")
    print()


def print_assembled_puzzle(result: dict):
    """Print the final 16-word puzzle with validation results."""
    print("\n" + "=" * 60)
    print("  ASSEMBLED PUZZLE (16 words)")
    print("=" * 60)

    all_words = []
    for i, g in enumerate(result["puzzle"]):
        color = DIFFICULTY_COLORS[i] if i < len(DIFFICULTY_COLORS) else f"Group {i+1}"
        print(f"\n  {color}: {g['category']}")
        print(f"    Words: {', '.join(g['words'])}")
        print(f"    Cohesion: {g['similarity']:.4f}")
        all_words.extend(g["words"])

    print(f"\n  Total unique words: {len(set(all_words))}")

    if result["valid"]:
        print("  Validation: PASSED -- unique solution confirmed")
    else:
        print("  Validation: FAILED -- ambiguous words detected:")
        for word, own, other, margin in result["ambiguous_words"]:
            print(
                f"    '{word}' assigned to [{own}] but fits [{other}] "
                f"better (margin={margin:+.4f})"
            )
        for category, issue_type, signal in result.get("difficulty_issues", []):
            print(
                f"    Group [{category}] rejected for being too obvious "
                f"({issue_type}={signal})"
            )

    # Print shuffled 4x4 grid
    random.shuffle(all_words)
    print(f"\n  Shuffled 4x4 Grid:")
    for row in range(4):
        cells = all_words[row * 4 : (row + 1) * 4]
        print(f"    {' | '.join(f'{w:^14s}' for w in cells)}")
    print()


# --------------- Main ---------------


def generate_one_puzzle(client: OpenAI, dataset: list[dict], embed_model: SentenceTransformer) -> dict | None:
    """Generate a single puzzle end-to-end. Returns puzzle dict or None on failure."""
    try:
        fewshot_examples = pick_fewshot_examples(dataset)
        fewshot_text = format_fewshot_examples(fewshot_examples)
        seed_words = pick_seed_words(dataset)

        story = generate_diversity_story(client, seed_words)

        root = generate_root_group(client, fewshot_text, story)
        groups = [root]

        used_overlap_words = []
        for i in range(2, 5):
            followup = generate_followup_group(
                client, fewshot_text, groups, i, used_overlap_words
            )
            groups.append(followup)
            used_overlap_words.append(followup.get("overlap_word", "").upper())

        # Deduplicate pools
        for g in groups:
            g["words"] = list(dict.fromkeys(g["words"]))

        # Step 1: Assemble the most semantically cohesive groups for validation.
        result = assemble_puzzle(groups, embed_model, target_difficulty="Yellow (Easiest)")
        if result is None:
            return None

        # Step 2: LLM re-ranks the 4 groups by perceived difficulty for display.
        ranked_puzzle = rank_difficulty_with_llm(client, result["puzzle"])

        # Build output structure
        overlaps = find_overlaps(groups)
        shared = {w: gis for w, gis in overlaps.items() if len(gis) > 1}

        all_words = [w for p in ranked_puzzle for w in p["words"]]
        shuffled = all_words[:]
        random.shuffle(shuffled)

        return {
            "seed_words": seed_words,
            "story": story,
            "groups": [
                {
                    "category": g["category"],
                    "candidates": g["words"],
                    "overlap_word": g.get("overlap_word"),
                    "source_group": g.get("source_group"),
                }
                for g in groups
            ],
            "overlap_words": {
                w: [groups[gi]["category"] for gi in gis]
                for w, gis in shared.items()
            },
            "puzzle": ranked_puzzle,
            "valid": result["valid"],
            "ambiguous_words": result["ambiguous_words"],
            "difficulty_issues": result.get("difficulty_issues", []),
            "shuffled_grid": shuffled,
        }
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def main():
    # NUM_PUZZLES = 100
    # OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles.json")

    client = make_client()
    dataset = load_dataset(DATASET_PATH)

    print("Loading embedding model...")
    embed_model = load_embedding_model()

    result = generate_one_puzzle(client, dataset, embed_model)
    if result is not None:
        print_header(result["seed_words"], result["story"])
        for i, g in enumerate(result["groups"], 1):
            print_group(g, i)
        print_results(result["groups"])
        print_assembled_puzzle(result)
    else:
        print("Failed to generate a valid puzzle.")
        
    # puzzles = []
    # failures = 0

    # print(f"Generating {NUM_PUZZLES} puzzles...")
    # for i in range(1, NUM_PUZZLES + 1):
    #     result = generate_one_puzzle(client, dataset, embed_model)
    #     if result is not None:
    #         puzzles.append(result)
    #         status = "valid" if result["valid"] else "invalid"
    #         print(f"  [{i}/{NUM_PUZZLES}] {status} — {len(puzzles)} saved")
    #     else:
    #         failures += 1
    #         print(f"  [{i}/{NUM_PUZZLES}] FAILED — skipped")

    # with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    #     json.dump(puzzles, f, ensure_ascii=False, indent=2)

    # print(f"\nDone. {len(puzzles)} puzzles saved to {OUTPUT_FILE} ({failures} failures)")

if __name__ == "__main__":
    main()

import json
import os
from functools import lru_cache

from openai import OpenAI
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def load_web_resources():
    """
    只在第一次请求时加载资源，后面复用。
    你可以按你自己的项目情况改这里。
    """
    client = make_client()

    dataset_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "NYT-Connections",
        "ConnectionsFinalDataset.json",
    )

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    return client, dataset, embed_model


def generate_one_puzzle_for_web():
    client, dataset, embed_model = load_web_resources()
    result = generate_one_puzzle(client, dataset, embed_model)

    if result is None:
        raise RuntimeError("Failed to generate puzzle.")

    return result
