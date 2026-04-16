"""Generate puzzles and append valid ones to a separate JSON file."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = Path(__file__).resolve().parent
PUZZLES_PATH = BASE_DIR / "puzzles.json"
VALID_OUTPUT_PATH = BASE_DIR / "generated_valid_puzzles.json"
INVALID_PATH = BASE_DIR / "invalid_puzzles.json"
DATASET_PATH = BASE_DIR / "NYT-Connections" / "ConnectionsFinalDataset.json"


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return data


def save_json_list(path: Path, data: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attempts",
        type=int,
        default=10,
        help="Number of generation attempts to run.",
    )
    parser.add_argument(
        "--valid-output",
        default=str(VALID_OUTPUT_PATH),
        help="JSON file that receives newly generated valid puzzles.",
    )
    parser.add_argument(
        "--invalid-output",
        default=str(INVALID_PATH),
        help="JSON file that receives newly generated invalid puzzles.",
    )
    parser.add_argument(
        "--all-output",
        default=None,
        help="Optional JSON file that receives every generated puzzle.",
    )
    args = parser.parse_args()

    if args.attempts <= 0:
        raise ValueError("--attempts must be positive.")
    if not os.getenv("LITELLM_TOKEN"):
        raise RuntimeError(
            "LITELLM_TOKEN is not set. Export it before running append_puzzles.py."
        )

    valid_output_path = Path(args.valid_output)
    invalid_output_path = Path(args.invalid_output)
    all_output_path = Path(args.all_output) if args.all_output else None

    existing_valid = load_json_list(valid_output_path)
    existing_invalid = load_json_list(invalid_output_path)
    existing_all = load_json_list(all_output_path) if all_output_path else []

    from generate_puzzle import generate_one_puzzle, load_dataset, load_embedding_model, make_client

    client = make_client()
    dataset = load_dataset(str(DATASET_PATH))
    print("Loading embedding model...")
    embed_model = load_embedding_model()

    new_valid: list[dict] = []
    new_invalid: list[dict] = []
    new_all: list[dict] = []
    failed = 0

    for attempt in range(1, args.attempts + 1):
        print(f"\n--- Attempt {attempt}/{args.attempts} ---", flush=True)
        result = generate_one_puzzle(client, dataset, embed_model)
        if result is None:
            failed += 1
            print("  -> FAILED (generation error)")
            continue

        is_valid = bool(result.get("valid"))
        new_all.append(result)
        if all_output_path:
            save_json_list(all_output_path, existing_all + new_all)

        if is_valid:
            new_valid.append(result)
            save_json_list(valid_output_path, existing_valid + new_valid)
        else:
            new_invalid.append(result)
            save_json_list(invalid_output_path, existing_invalid + new_invalid)

        status = "VALID" if is_valid else "INVALID"
        print(
            f"  -> {status} | valid_saved={len(new_valid)} | "
            f"invalid_saved={len(new_invalid)} | failed={failed}",
            flush=True,
        )

    final_valid_puzzles = load_json_list(valid_output_path)
    final_invalid_puzzles = load_json_list(invalid_output_path)
    print("\nDone.")
    print(f"Generated attempts: {args.attempts}")
    print(f"New valid puzzles saved: {len(new_valid)}")
    print(f"New invalid puzzles saved: {len(new_invalid)}")
    print(f"Failed attempts: {failed}")
    print(f"{valid_output_path.name} total: {len(final_valid_puzzles)}")
    print(f"{invalid_output_path.name} total: {len(final_invalid_puzzles)}")
    if all_output_path:
        final_all = load_json_list(all_output_path)
        print(f"{all_output_path.name} total: {len(final_all)}")


if __name__ == "__main__":
    main()
