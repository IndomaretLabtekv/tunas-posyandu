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

<!-- TABULAR_CLOSURE_START -->
## TAB-12 — Top-K boundary tie sensitivity

The production rule is unchanged: exact K with deterministic `child_id` tie-breaking.
The ranges below vary only membership inside the cutoff-score tie group.

| evaluation | K | mean / max cutoff tie | mean observed recall | mean exact recall bounds | max range width | worst seed |
| --- | --- | --- | --- | --- | --- | --- |
| grouped | 5% | 5.2 / 20 | 0.1531 | 0.1300–0.1608 | 0.1538 | 42 |
| grouped | 10% | 5.0 / 12 | 0.2587 | 0.2587–0.2741 | 0.0769 | 42 |
| grouped | 20% | 6.4 / 28 | 0.4821 | 0.4744–0.4975 | 0.1154 | 42 |
| temporal | 5% | 11.0 / 47 | 0.1627 | 0.1571–0.1712 | 0.0643 | 2026 |
| temporal | 10% | 16.4 / 54 | 0.2573 | 0.2502–0.2772 | 0.1286 | 2026 |
| temporal | 20% | 23.6 / 65 | 0.4358 | 0.4141–0.4464 | 0.0897 | 2718 |

## TAB-08 — Synthetic input robustness

The frozen M2 model was trained on unperturbed data. Only measurements available by each
prediction date were corrupted; WHO HAZ and dependent features were then recomputed.

| evaluation | scenario | AUPRC | coverage | ΔAUPRC | ΔRecall@20% | Recall@20% |
| --- | --- | --- | --- | --- | --- | --- |
| grouped | baseline | 0.2735 ± 0.0947 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.4821 ± 0.0994 |
| grouped | length_noise_sigma_0_5cm | 0.2936 ± 0.1212 | 1.0000 ± 0.0000 | 0.0201 ± 0.0668 | 0.0338 ± 0.0689 | 0.5159 ± 0.0802 |
| grouped | length_noise_sigma_1_0cm | 0.2160 ± 0.0219 | 1.0000 ± 0.0000 | -0.0574 ± 0.0978 | -0.0608 ± 0.1082 | 0.4213 ± 0.0611 |
| grouped | length_noise_sigma_2_0cm | 0.1536 ± 0.0432 | 1.0000 ± 0.0000 | -0.1199 ± 0.0861 | -0.1608 ± 0.1230 | 0.3213 ± 0.1353 |
| grouped | length_missing_plus_10pct | 0.2752 ± 0.0823 | 1.0000 ± 0.0000 | 0.0018 ± 0.0271 | -0.0262 ± 0.0251 | 0.4559 ± 0.0975 |
| grouped | length_missing_plus_20pct | 0.2391 ± 0.0923 | 1.0000 ± 0.0000 | -0.0344 ± 0.0347 | -0.0716 ± 0.0735 | 0.4105 ± 0.1095 |
| grouped | length_missing_plus_30pct | 0.2447 ± 0.0696 | 1.0000 ± 0.0000 | -0.0288 ± 0.0597 | -0.0012 ± 0.0966 | 0.4809 ± 0.1157 |
| grouped | current_measurement_missing | 0.1465 ± 0.0363 | 1.0000 ± 0.0000 | -0.1270 ± 0.0907 | -0.2294 ± 0.1893 | 0.2527 ± 0.1315 |
| temporal | baseline | 0.2976 ± 0.0311 | 1.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.4358 ± 0.0345 |
| temporal | length_noise_sigma_0_5cm | 0.2636 ± 0.0366 | 1.0000 ± 0.0000 | -0.0340 ± 0.0244 | -0.0317 ± 0.0242 | 0.4042 ± 0.0405 |
| temporal | length_noise_sigma_1_0cm | 0.2262 ± 0.0349 | 1.0000 ± 0.0000 | -0.0714 ± 0.0341 | -0.0970 ± 0.0419 | 0.3388 ± 0.0483 |
| temporal | length_noise_sigma_2_0cm | 0.1860 ± 0.0139 | 1.0000 ± 0.0000 | -0.1116 ± 0.0326 | -0.1556 ± 0.0744 | 0.2802 ± 0.0448 |
| temporal | length_missing_plus_10pct | 0.2932 ± 0.0346 | 1.0000 ± 0.0000 | -0.0044 ± 0.0088 | -0.0144 ± 0.0208 | 0.4214 ± 0.0408 |
| temporal | length_missing_plus_20pct | 0.2743 ± 0.0410 | 1.0000 ± 0.0000 | -0.0233 ± 0.0139 | -0.0330 ± 0.0259 | 0.4028 ± 0.0480 |
| temporal | length_missing_plus_30pct | 0.2477 ± 0.0366 | 1.0000 ± 0.0000 | -0.0499 ± 0.0211 | -0.0760 ± 0.0296 | 0.3599 ± 0.0575 |
| temporal | current_measurement_missing | 0.2017 ± 0.0293 | 1.0000 ± 0.0000 | -0.0960 ± 0.0476 | -0.1309 ± 0.0713 | 0.3049 ± 0.0720 |

`coverage` is the fraction of intended children receiving a finite model score. A valid
manual length remains an observed measurement and is not the same as
`current_measurement_missing`.

## TAB-10 — Current-environment inference benchmark

- Environment: Intel(R) Core(TM) Ultra 7 155H;
  Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39; Python 3.12.3.
- Required model artifact: 14150 bytes
  (0.0135 MiB); schema embedded.
- Interpreter startup and CSV I/O are excluded from warm prediction timings.

| measurement | batch_size | repetitions | median_ms | p95_ms | throughput_rows_per_second |
| --- | --- | --- | --- | --- | --- |
| artifact_load |  | 100 | 9.5787 | 11.5132 |  |
| warm_predict | 1 | 200 | 1.1604 | 1.8092 | 861.8 |
| warm_predict | 10 | 200 | 1.0540 | 2.2325 | 9488.0 |
| warm_predict | 100 | 200 | 0.9431 | 1.2131 | 106032.3 |
| warm_predict | 240 | 200 | 0.9860 | 1.4859 | 243404.7 |
| score_and_exact_top20_ranking | 240 | 200 | 1.0680 | 1.5690 | 224717.9 |

## Clean-source reproducibility verification

The committed `TAB-FINAL-01` was regenerated in a detached clean worktree at
`e0f5902ec68b0b90f3f5ddbb227259705c892556` with `git_dirty=false`. All
11 compared CSV artifacts were numerically equal within
`1e-12`; 11/11
were byte-identical. WHO validation JSON also matched exactly.

## Closure limitations

Robustness is sensitivity analysis on synthetic cohorts, not evidence of clinical
robustness. Latency applies only to the recorded machine. Equal-score cutoff groups can
make exact-K membership and Recall@K materially tie-break-sensitive even though list size
and ordering remain deterministic. The frozen schema contains `measured_by_cv_t`; TAB-08
does not equate a valid manual measurement with a missing measurement and makes no claim
that scores are invariant to the source flag.
<!-- TABULAR_CLOSURE_END -->
