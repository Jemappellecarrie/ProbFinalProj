# GPT Editorial Recovery Review Bundle

This bundle is for reviewing whether the latest editorial-quality recovery pass moved the Connections generator in the intended direction.

What GPT should judge:
- Did the ranking policy stop over-rewarding formulaic balanced-mixed boards?
- Did family-level dedupe/diversity controls become real and visible?
- Did the new top boards become more editor-like or merely narrower?
- Is the current outcome closer to the intended editorial standard?
- Does the evidence support "improved editorial alignment but unresolved diversity/yield"?

Suggested review order:
1. `01_spec_context/editorial_quality_recovery.md`
2. `03_before_after_reports/editorial_recovery_compare/`
3. `03_before_after_reports/post_calibration_run/top_k.json`
4. `03_before_after_reports/editorial_recovery_run/top_k.json`
5. `03_before_after_reports/post_calibration_run/quality_audit_report.json`
6. `03_before_after_reports/editorial_recovery_run/quality_audit_report.json`
7. `02_code_changes/`
8. `04_human_review_materials/`
9. `05_tests/`

Current evidence snapshot:
- The editorial-recovery rerun used the same acceptance lane: 200 requests, base seed 17, top-k 20, candidate-pool limit 30.
- Machine-side quality improved versus the prior post-calibration run: the generated top-k moved from all-borderline to 5 accept / 3 borderline.
- The rerun became much narrower: only 8 unique generated boards made it through the final run.
- The regenerated blind-review packet therefore has an honest shortfall: 8 generated + 20 benchmark = 28 total boards, not 40.
- The right high-level claim is likely "editorial ranking improved, but diversity/yield is still not healthy enough."

Important caution:
- Do not open `04_human_review_materials/blind_review/HIDDEN_answer_key/` during the first-pass blind assessment.
- Do not treat the hidden keys as evidence that the generator passed the human gate.

What is intentionally omitted:
- Large raw candidate-pool artifacts like `candidate_pool.json` and the full accepted/borderline record dumps.
- The goal here is focused review of the policy change, top-k outcome, and before/after evidence, not full repository archaeology.
