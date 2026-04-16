from flask import Flask, jsonify, render_template
from generate_puzzle import generate_one_puzzle_for_web
import json
import os
import random

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUZZLES_JSON_PATH = os.getenv(
    "PUZZLES_JSON_PATH",
    os.path.join(BASE_DIR, "puzzles.json"),
)


def load_prebuilt_puzzles():
    with open(PUZZLES_JSON_PATH, "r", encoding="utf-8") as f:
        puzzles = json.load(f)

    # 如果你只想给用户 valid=True 的题，就取消下面这段注释
    # puzzles = [p for p in puzzles if p.get("valid", False)]

    if not puzzles:
        raise RuntimeError("No puzzles found in puzzles.json")

    return puzzles


PREBUILT_PUZZLES = load_prebuilt_puzzles()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate-puzzle", methods=["POST"])
def api_generate_puzzle():
    try:
        puzzle = generate_one_puzzle_for_web()
        return jsonify(puzzle)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/random-puzzle", methods=["POST"])
def api_random_puzzle():
    try:
        puzzle = random.choice(PREBUILT_PUZZLES)
        return jsonify(puzzle)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
