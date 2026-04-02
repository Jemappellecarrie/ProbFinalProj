# Files To Send For GPT Scoring

这组文件是从 `assets/` 里单独整理出来的“评分输入”版本，方便直接发给 GPT。

## 1. 盲评打分

目录：`01_blind_review_inputs/`

发送这些文件：

- `blind_review_instructions.md`
- `blind_review_packet.json`
- `blind_review_packet.csv`
- `reviewer_template.csv`

用途：

- 让 GPT 作为编辑/评审者，对 40 个题板做盲评
- 不要同时发送答案键

## 2. 解题试玩

目录：`02_solve_playtest_inputs/`

发送这些文件：

- `solve_playtest_instructions.md`
- `solve_playtest_packet.json`
- `solve_playtest_template.csv`

用途：

- 让 GPT 作为玩家，根据 packet 里的题板做 solve-playtest
- 记录是否能解出、是否公平、是否自然、是否像 NYT

## 3. 可选的专家分析材料

目录：`03_optional_expert_analysis/`

可选发送：

- `top_k.json`
- `accepted.json`
- `borderline.json`

用途：

- 这组更适合让 GPT 做“题板质量分析 / 排名分析 / top-k 复核”
- 它们不是盲评或解题试玩的必要输入

## 不要发给 GPT 的文件

不要在第一轮评分时发送这些文件：

- `assets/04_blind_review/HIDDEN_answer_key/blind_review_key.json`
- `assets/05_solve_playtest/HIDDEN_answer_key/solve_playtest_key.json`
- `assets/04_blind_review/blind_review_results.json`
- `assets/04_blind_review/blind_review_results.md`
- `assets/04_blind_review/final_quality_gate.json`
- `assets/04_blind_review/final_quality_gate.md`
- `assets/05_solve_playtest/solve_playtest_results.json`
- `assets/05_solve_playtest/solve_playtest_results.md`
