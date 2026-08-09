# Final Tabular Experiment Results

## Environment

- Python: 3.12.3
- Git commit: `30fa13b9bd3bb355c0d641bea00381115add536d`
- Git working tree dirty during run: `true`
- Packages: numpy 2.4.6, pandas 3.0.5, scikit-learn 1.9.0, lightgbm 4.7.0, shap 0.52.0, joblib 1.5.3
- Config: `TAB-FINAL-01`

## WHO validation

- Official source: WHO Child Growth Standards `lenanthro.sas7bdat` from the official SAS macro package.
- Scope: recumbent length-for-age, female/male, ages 0–730 days.
- Independent checks: 18 cases from separate WHO simplified field tables.
- Result: all passed; maximum absolute HAZ difference 0.0256 (tolerance 0.05 for 0.1 cm rounded reference lengths).

## Dataset

- Generator: `posyandu_synth_v1`, 1200 requested children per seed.
- Seeds: 42, 314, 1618, 2026, 2718.
- The target is prospective deterioration at 91 ± 42 days, not current stunting status.

| seed | n_children | n_visits | eligible_rows | target_prevalence |
| --- | --- | --- | --- | --- |
| 42 | 1200 | 22779 | 19183 | 0.1482 |
| 314 | 1200 | 22983 | 19481 | 0.1431 |
| 1618 | 1200 | 22976 | 19447 | 0.1459 |
| 2026 | 1200 | 22903 | 19262 | 0.1458 |
| 2718 | 1200 | 22953 | 19465 | 0.1436 |

## Evaluation

One index visit per child is ranked globally. Exact-K selection uses `child_id` as a deterministic tie-break. Values are mean ± sample standard deviation over 5 seeds.

### Grouped child holdout

| Model | auprc | lift@20% | precision@20% | recall@20% |
| --- | --- | --- | --- | --- |
| B0_haz_only | 0.1626 ± 0.0464 | 1.0482 ± 0.5010 | 0.1042 ± 0.0466 | 0.2096 ± 0.1002 |
| B1_haz_slope | 0.1797 ± 0.0436 | 1.4944 ± 0.4836 | 0.1500 ± 0.0401 | 0.2989 ± 0.0967 |
| B2_logreg | 0.1622 ± 0.0403 | 1.3704 ± 0.1820 | 0.1417 ± 0.0309 | 0.2741 ± 0.0364 |
| M1_snapshot | 0.2291 ± 0.0546 | 2.0620 ± 0.3277 | 0.2125 ± 0.0475 | 0.4124 ± 0.0655 |
| M2_plus_trajectory | 0.2735 ± 0.0947 | 2.4104 ± 0.4969 | 0.2500 ± 0.0691 | 0.4821 ± 0.0994 |
| M3_plus_contextual | 0.2268 ± 0.0556 | 2.2948 ± 0.4101 | 0.2375 ± 0.0600 | 0.4590 ± 0.0820 |

### Temporal holdout with label-maturity purge

| Model | auprc | lift@20% | precision@20% | recall@20% |
| --- | --- | --- | --- | --- |
| B0_haz_only | 0.1853 ± 0.0232 | 1.2472 ± 0.2017 | 0.1680 ± 0.0365 | 0.2493 ± 0.0403 |
| B1_haz_slope | 0.2213 ± 0.0513 | 1.5404 ± 0.4186 | 0.2082 ± 0.0664 | 0.3080 ± 0.0839 |
| B2_logreg | 0.1616 ± 0.0119 | 1.2040 ± 0.1704 | 0.1608 ± 0.0204 | 0.2407 ± 0.0340 |
| M1_snapshot | 0.2237 ± 0.0303 | 1.7692 ± 0.2368 | 0.2377 ± 0.0396 | 0.3537 ± 0.0475 |
| M2_plus_trajectory | 0.2976 ± 0.0311 | 2.1798 ± 0.1738 | 0.2913 ± 0.0161 | 0.4358 ± 0.0345 |
| M3_plus_contextual | 0.2979 ± 0.0506 | 2.2256 ± 0.2760 | 0.2979 ± 0.0375 | 0.4449 ± 0.0550 |

## Primary model

`M2_plus_trajectory` was pre-specified as primary and remains primary regardless of which model has the best final test metric. The persisted artifact is `results/tabular/final/primary_model.joblib`.

## Robustness and ablation

| evaluation | comparison | metric | mean_std |
| --- | --- | --- | --- |
| grouped | M2_minus_M1_trajectory | auprc | +0.0444 ± 0.0716 |
| grouped | M2_minus_M1_trajectory | recall@20% | +0.0697 ± 0.0774 |
| grouped | M3_minus_M2_contextual | auprc | -0.0467 ± 0.0531 |
| grouped | M3_minus_M2_contextual | recall@20% | -0.0231 ± 0.0353 |
| temporal | M2_minus_M1_trajectory | auprc | +0.0739 ± 0.0281 |
| temporal | M2_minus_M1_trajectory | recall@20% | +0.0821 ± 0.0680 |
| temporal | M3_minus_M2_contextual | auprc | +0.0003 ± 0.0204 |
| temporal | M3_minus_M2_contextual | recall@20% | +0.0091 ± 0.0342 |

Positive `M2_minus_M1_trajectory` values mean trajectory features add ranking signal over the snapshot model within this controlled synthetic environment. They do not establish clinical effectiveness.

## Error analysis

| group | n |
| --- | --- |
| true_positive | 9 |
| false_negative | 17 |
| false_positive | 39 |
| true_negative | 175 |

Representative cases are selected by deterministic rules in `tab07_representative_cases.csv`. A zero candidate count means that category did not occur in the primary grouped test set.

| case_type | candidate_count | selected_count |
| --- | --- | --- |
| high_priority_false_positive | 39 | 3 |
| missed_positive | 17 | 3 |
| capacity_boundary | 4 | 4 |
| trajectory_rank_change | 239 | 3 |
| short_or_sparse_history | 0 | 0 |

Top global M2 feature attributions (raw-model log-odds SHAP; non-causal):

| feature | mean_abs_shap |
| --- | --- |
| haz_delta_1visit | 0.04499 |
| haz_slope_per_month | 0.02313 |
| haz_t | 0.01957 |
| months_since_haz_peak | 0.01694 |
| haz_delta_3months | 0.01272 |

## Limitations

Performance on these synthetic cohorts validates pipeline and mechanism behavior only. It is not external clinical validation, does not demonstrate benefit on real children, and is not evidence that Tunas improves real-world child-health outcomes. The generator is a simplified world model, and the operational deterioration threshold has not been clinically validated.
