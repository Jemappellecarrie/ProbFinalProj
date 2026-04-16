"""Generate puzzles for a fixed number of attempts and report validity counts."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_puzzle import make_client, load_dataset, load_embedding_model, generate_one_puzzle, DATASET_PATH


def save_valid_puzzles(output_path, valid_puzzles):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(valid_puzzles, f, ensure_ascii=False, indent=2)


def save_invalid_puzzles(output_path, invalid_puzzles):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(invalid_puzzles, f, ensure_ascii=False, indent=2)


def main():
    target_attempts = 10
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles.json")
    invalid_output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "invalid_puzzles.json",
    )

    client = make_client()
    dataset = load_dataset(DATASET_PATH)
    print("Loading embedding model...")
    embed_model = load_embedding_model()

    valid_puzzles = []
    invalid_puzzles = []
    all_puzzles = []
    failed_attempts = 0
    attempts = 0

    # Initialize the output file so progress can be monitored live.
    save_valid_puzzles(output_path, valid_puzzles)
    save_invalid_puzzles(invalid_output_path, invalid_puzzles)

    while attempts < target_attempts:
        attempts += 1
        print(
            f"\n--- Attempt {attempts}/{target_attempts} | "
            f"Valid: {len(valid_puzzles)} | Invalid: {len(invalid_puzzles)} | Failed: {failed_attempts} ---"
        )
        result = generate_one_puzzle(client, dataset, embed_model)
        if result is None:
            print("  -> FAILED (generation error), skipping")
            failed_attempts += 1
            continue

        all_puzzles.append(result)
        amb = len(result.get("ambiguous_words", []))

        if result["valid"]:
            valid_puzzles.append(result)
            save_valid_puzzles(output_path, valid_puzzles)
            print(
                f"  -> VALID! "
                f"(valid={len(valid_puzzles)}, invalid={len(invalid_puzzles)}, failed={failed_attempts})"
            )
        else:
            invalid_puzzles.append(result)
            save_invalid_puzzles(invalid_output_path, invalid_puzzles)
            print(
                f"  -> INVALID ({amb} ambiguous words) "
                f"(valid={len(valid_puzzles)}, invalid={len(invalid_puzzles)}, failed={failed_attempts})"
            )

        # Show group summary
        for g in result["puzzle"]:
            color = g.get("color", "?")
            print(f"     {color}: {g['category']} -> {', '.join(g['words'])}")

    save_valid_puzzles(output_path, valid_puzzles)
    save_invalid_puzzles(invalid_output_path, invalid_puzzles)

    print(f"\n{'='*60}")
    print(f"Done after {attempts} attempts")
    print(f"Valid puzzles: {len(valid_puzzles)} saved to puzzles.json")
    print(f"Invalid puzzles: {len(invalid_puzzles)} saved to invalid_puzzles.json")
    print(f"Failed attempts: {failed_attempts}")
    print(
        f"Observed valid rate: {len(valid_puzzles)}/{len(all_puzzles)} "
        f"({100*len(valid_puzzles)/max(len(all_puzzles),1):.0f}%)"
    )

if __name__ == "__main__":
    main()
