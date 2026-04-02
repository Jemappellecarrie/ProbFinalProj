# NYT Benchmark Quality Audit

- Generated run: `final_quality_acceptance`
- Generated top-k boards reviewed automatically: 20
- Benchmark holdout boards reviewed automatically: 126
- Split policy: primary oldest 80% calibration / newest 20% holdout; newer supplement-only boards freshness split

## Machine Summary
- Generated high-confidence top-k rate: 0.000
- Generated top-k quality buckets: {"accepted_borderline": 20, "accepted_high_confidence": 0, "rejected": 0}
- Benchmark holdout quality buckets under current policy: {"accepted_borderline": 83, "accepted_high_confidence": 34, "rejected": 9}

## Comparison Highlights
- Verifier decision L1 distance: 0.6825
- Mechanism mix L1 distance: 1.3611
- Human blind review is still required for the final 40% publishable gate.
