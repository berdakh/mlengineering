# Exercise solutions

Reference solutions for every guided lab and independent challenge, in notebook order, and the
plausible wrong submissions each check suite is verified to reject. See [README](README.md) for how
to use this file and the confidence markers.

---

# Notebook 03 — From script to installable package: project structure and environments

✅ **Guided lab:** reference in [`solutions/labs/w1d3_package_structure/lab/`](labs/w1d3_package_structure/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w1d3_package_structure/challenge/`](labs/w1d3_package_structure/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `flat_layout` — flat layout
- `hardcoded_data_path` — `--data` is parsed but ignored
- `leaky_scaling` — refactored, but the scaler is still fitted on all rows
- `missing_dependency` — scikit-learn is imported but not declared
- `wrong_entry_point` — entry point names a callable that does not exist

Wrong challenge submissions the checks reject:

- `features_errors_unhandled` — the new subcommand bypasses the error handling
- `features_file_unvalidated` — `load_features` trusts whatever file it is given
- `no_main_module` — no `__main__.py`
- `out_dir_not_created` — `--out` only works if the directory already exists

---

# Notebook 04 — Configuration, logging and reproducible runs

✅ **Guided lab:** reference in [`solutions/labs/w1d4_config_logging/lab/`](labs/w1d4_config_logging/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w1d4_config_logging/challenge/`](labs/w1d4_config_logging/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `basicconfig_at_import` — basicconfig_at_import
- `logs_on_stdout` — logs_on_stdout
- `overrides_ignored` — overrides_ignored
- `seed_not_threaded` — seed_not_threaded
- `snapshot_before_overrides` — snapshot_before_overrides
- `unknown_keys_accepted` — unknown_keys_accepted

Wrong challenge submissions the checks reject:

- `delta_reversed` — delta_reversed
- `same_data_by_path` — same_data_by_path
- `top_level_only` — top_level_only

---

# Notebook 05 — Testing ML code with pytest: what a unit test can and cannot tell you

✅ **Guided lab:** reference in [`solutions/labs/w1d5_testing_ml_code/lab/`](labs/w1d5_testing_ml_code/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w1d5_testing_ml_code/challenge/`](labs/w1d5_testing_ml_code/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `depends_on_repo_data` — depends_on_repo_data
- `end_to_end_metric_only` — end_to_end_metric_only
- `loose_tolerances` — loose_tolerances
- `runs_without_error` — runs_without_error
- `self_consistency_only` — self_consistency_only

Wrong challenge submissions the checks reject:

- `happy_path_tests_only` — happy_path_tests_only
- `impl_still_drops_final_event` — impl_still_drops_final_event
- `tests_encode_inclusive_threshold` — tests_encode_inclusive_threshold

---

# Notebook 06 — Independent refactor: a real exploratory notebook becomes the project skeleton

✅ **Guided lab:** reference in [`solutions/labs/w1d6_notebook_to_package/lab/`](labs/w1d6_notebook_to_package/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w1d6_notebook_to_package/challenge/`](labs/w1d6_notebook_to_package/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `dropna_loses_normal` — dropna_loses_normal
- `gitignore_misses_data` — gitignore_misses_data
- `global_time_index` — global_time_index
- `positional_ids` — positional_ids
- `positional_rename` — positional_rename
- `stdout_noise` — stdout_noise
- `tests_need_download` — tests_need_download

Wrong challenge submissions the checks reject:

- `cli_ignores_threshold` — cli_ignores_threshold
- `gap_as_timedelta` — gap_as_timedelta
- `gaps_cross_experiments` — gaps_cross_experiments
- `inclusive_threshold` — inclusive_threshold

---

# Notebook 07 — SQL I: grain, joins, aggregation and NULL semantics

✅ **Guided lab:** reference in [`solutions/labs/w2d1_sql_joins_grain/lab/`](labs/w2d1_sql_joins_grain/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d1_sql_joins_grain/challenge/`](labs/w2d1_sql_joins_grain/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `q1_count_star` — q1_count_star
- `q2_not_in_null` — q2_not_in_null
- `q3_fanout_join` — q3_fanout_join
- `q4_where_filter` — q4_where_filter
- `q7_inner_join_half_fix` — q7_inner_join_half_fix

Wrong challenge submissions the checks reject:

- `c1_key_not_minimal` — c1_key_not_minimal
- `c2_count_not_distinct` — c2_count_not_distinct
- `c3_inner_join` — c3_inner_join
- `c4_fanout` — c4_fanout

---

# Notebook 08 — SQL II: CTEs, window functions and time-series queries

✅ **Guided lab:** reference in [`solutions/labs/w2d2_sql_windows_timeseries/lab/`](labs/w2d2_sql_windows_timeseries/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d2_sql_windows_timeseries/challenge/`](labs/w2d2_sql_windows_timeseries/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `asof_inner_join_drops_rows` — asof_inner_join_drops_rows
- `asof_uses_latest_calibration` — asof_uses_latest_calibration
- `default_range_frame` — default_range_frame
- `islands_no_partition` — islands_no_partition
- `pandas_window_open_on_left` — pandas_window_open_on_left
- `rows_window_on_irregular_time` — rows_window_on_irregular_time
- `top1_with_ties` — top1_with_ties

Wrong challenge submissions the checks reject:

- `centered_window` — centered_window
- `fault_any_time` — fault_any_time
- `nearest_reading` — nearest_reading

---

# Notebook 09 — pandas ingestion, schemas and data-quality checks (project data arrives)

✅ **Guided lab:** reference in [`solutions/labs/w2d3_data_quality_ingestion/lab/`](labs/w2d3_data_quality_ingestion/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d3_data_quality_ingestion/challenge/`](labs/w2d3_data_quality_ingestion/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `gaps_across_experiments` — gaps_across_experiments
- `silent_repair` — silent_repair
- `timestamp_in_provenance` — timestamp_in_provenance
- `writes_despite_errors` — writes_despite_errors

Wrong challenge submissions the checks reject:

- `crashes_on_unparseable` — crashes_on_unparseable
- `nan_passes_silently` — nan_passes_silently
- `single_column_rules_only` — single_column_rules_only
- `stops_at_first_failure` — stops_at_first_failure

---

# Notebook 10 — Problem framing and versioned split definitions

✅ **Guided lab:** reference in [`solutions/labs/w2d4_problem_framing_splits/lab/`](labs/w2d4_problem_framing_splits/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d4_problem_framing_splits/challenge/`](labs/w2d4_problem_framing_splits/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `anomaly_free_in_test` — anomaly_free_in_test
- `family_missing_from_test` — family_missing_from_test
- `nondeterministic` — nondeterministic
- `overwrites_frozen_manifest` — overwrites_frozen_manifest
- `row_level_split` — row_level_split
- `validate_checks_overlap_only` — validate_checks_overlap_only

Wrong challenge submissions the checks reject:

- `heldout_history_in_train` — heldout_history_in_train
- `label_notna_test` — label_notna_test
- `late_joiners_called_known` — late_joiners_called_known
- `no_purge_gap` — no_purge_gap
- `random_row_split` — random_row_split

---

# Notebook 11 — Reproducible feature generation without look-ahead

✅ **Guided lab:** reference in [`solutions/labs/w2d5_feature_pipeline/lab/`](labs/w2d5_feature_pipeline/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d5_feature_pipeline/challenge/`](labs/w2d5_feature_pipeline/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `cache_key_ignores_params` — cache_key_ignores_params
- `centred_window` — centred_window
- `gap_ignored` — gap_ignored
- `stats_from_transformed_data` — stats_from_transformed_data
- `windows_cross_experiments` — windows_cross_experiments

Wrong challenge submissions the checks reject:

- `centred_time_window` — centred_time_window
- `closed_both_ends` — closed_both_ends
- `outage_not_reset` — outage_not_reset
- `row_count_window` — row_count_window

---

# Notebook 12 — Strong simple baselines and metrics that match the decision

✅ **Guided lab:** reference in [`solutions/labs/w2d6_baselines_metrics/lab/`](labs/w2d6_baselines_metrics/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w2d6_baselines_metrics/challenge/`](labs/w2d6_baselines_metrics/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `diagonal_covariance` — diagonal_covariance
- `pr_auc_from_hard_labels` — pr_auc_from_hard_labels
- `score_is_normality` — score_is_normality
- `stats_refit_on_scored_data` — stats_refit_on_scored_data
- `threshold_tuned_on_test` — threshold_tuned_on_test

Wrong challenge submissions the checks reject:

- `balanced_class_weight` — balanced_class_weight
- `brier_on_hard_labels` — brier_on_hard_labels
- `random_validation_split` — random_validation_split
- `threshold_ignores_success_rate` — threshold_ignores_success_rate

---

# Notebook 13 — Leakage: a taxonomy and prevention by construction

✅ **Guided lab:** reference in [`solutions/labs/w3d1_leakage/lab/`](labs/w3d1_leakage/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d1_leakage/challenge/`](labs/w3d1_leakage/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `clock_search_pools_experiments` — clock_search_pools_experiments
- `keeps_customer_late_rate` — keeps_customer_late_rate
- `keeps_ledger_ref` — keeps_ledger_ref
- `keeps_reminders_sent` — keeps_reminders_sent
- `no_dedupe` — no_dedupe
- `overlap_requires_equal_labels` — overlap_requires_equal_labels
- `random_split` — random_split
- `repair_moves_dev_into_test` — repair_moves_dev_into_test
- `scaling_fitted_on_all_rows` — scaling_fitted_on_all_rows
- `validate_trusts_manifest` — validate_trusts_manifest

Wrong challenge submissions the checks reject:

- `best_of_n_on_test` — best_of_n_on_test
- `prescreen_on_all_rows` — prescreen_on_all_rows
- `reports_in_sample_auc` — reports_in_sample_auc

---

# Notebook 14 — Group-aware and temporal validation

✅ **Guided lab:** reference in [`solutions/labs/w3d2_group_temporal_validation/lab/`](labs/w3d2_group_temporal_validation/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d2_group_temporal_validation/challenge/`](labs/w3d2_group_temporal_validation/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `family_holdout_leaks_overlap` — Mutant `family_holdout_leaks_overlap`
- `groups_leak` — Mutant `groups_leak`
- `no_embargo` — Mutant `no_embargo`
- `purge_ignores_window` — Mutant `purge_ignores_window`
- `shuffled_time_split` — Mutant `shuffled_time_split`
- `test_in_training` — Mutant `test_in_training`

Wrong challenge submissions the checks reject:

- `no_label_purge` — Mutant `no_label_purge`
- `random_validation_rows` — Mutant `random_validation_rows`
- `young_stores_as_new` — Mutant `young_stores_as_new`

---

# Notebook 15 — Hyperparameter and threshold selection without fooling yourself

✅ **Guided lab:** reference in [`solutions/labs/w3d3_hyperparameter_selection/lab/`](labs/w3d3_hyperparameter_selection/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d3_hyperparameter_selection/challenge/`](labs/w3d3_hyperparameter_selection/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `best_trial_as_estimate` — the winner's search score is reported as the estimate
- `outer_fold_in_inner_search` — outer fold takes part in the inner search
- `row_kfold_inner` — inner folds are row-wise, not grouped
- `threshold_on_test` — threshold chosen on the test data
- `trains_on_everything_else` — the training set is "everything except the validation fold"

Wrong challenge submissions the checks reject:

- `dev_mean_as_estimate` — the chosen trial's own dev mean is reported as the estimate
- `peeked_then_switched` — several test looks
- `picks_fewest_parameters` — "prefer simpler models" taken to mean "ignore the scores"
- `rho_ignored` — correlation between candidates ignored

---

# Notebook 16 — Point-level versus event-level evaluation for detection

✅ **Guided lab:** reference in [`solutions/labs/w3d4_point_vs_event_evaluation/lab/`](labs/w3d4_point_vs_event_evaluation/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d4_point_vs_event_evaluation/challenge/`](labs/w3d4_point_vs_event_evaluation/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `confirmation_ignored` — delay measured to the alarm's first row, whatever the persistence requirement
- `early_alarm_counts` — any overlap is a detection
- `filter_before_merge` — duration filter applied before merging
- `fragments_as_hits` — every fragment is a true positive
- `hours_from_rows` — hours computed from the row count
- `inclusive_event_end` — inclusive event end
- `missed_delays_dropped` — delays of detected events only

Wrong challenge submissions the checks reject:

- `budget_ignored` — budget ignored
- `fewest_false_alarms_wins` — minimise false alarms, full stop
- `infeasible_reported_feasible` — fallback presented as success
- `point_estimate_as_bound` — the observed rate reported as the upper bound

---

# Notebook 17 — Uncertainty: cluster bootstrap, paired comparisons, small-n honesty

✅ **Guided lab:** reference in [`solutions/labs/w3d5_uncertainty/lab/`](labs/w3d5_uncertainty/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d5_uncertainty/challenge/`](labs/w3d5_uncertainty/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `row_level_resampling` — row-level resampling
- `seed_ignored` — seed accepted but ignored
- `unpaired_diff` — unpaired resampling in the "paired" difference
- `wald_interval` — Wald (normal-approximation) interval under the name `wilson_interval`

Wrong challenge submissions the checks reject:

- `largest_candidate` — returns the last sufficient candidate instead of the smallest
- `one_sided_test` — one-sided test reported as two-sided
- `seed_ignored` — seed ignored

---

# Notebook 18 — Error analysis and timed transfer exercise

✅ **Guided lab:** reference in [`solutions/labs/w3d6_error_analysis_transfer/lab/`](labs/w3d6_error_analysis_transfer/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w3d6_error_analysis_transfer/challenge/`](labs/w3d6_error_analysis_transfer/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `empty_slice_is_zero` — an empty slice reports 0.0
- `late_called_miss` — a late detection is called a miss
- `slice_pooled_over_rows` — slice value pooled over rows
- `undefined_precision_is_zero` — undefined ratios are 0.0

Wrong challenge submissions the checks reject:

- `global_top_k` — one global top-k instead of k per week
- `labels_not_yet_known` — temporal split without the label delay
- `late_rate_under_another_name` — export-time aggregate used under another name
- `random_row_split` — random 80/20 row split
- `uses_reminders_sent` — `reminders_sent` as a feature

---

# Notebook 19 — Time-series fundamentals and forecast-residual detectors

✅ **Guided lab:** reference in [`solutions/labs/w4d1_timeseries_fundamentals/lab/`](labs/w4d1_timeseries_fundamentals/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d1_timeseries_fundamentals/challenge/`](labs/w4d1_timeseries_fundamentals/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `acf_no_mean_removal` — Autocorrelation without removing the mean
- `ar_lag_includes_present` — AR design matrix shifted by one row
- `ar_no_intercept` — AR fitted without an intercept
- `cusum_no_floor` — CUSUM sums without the floor at zero
- `sigma_from_series` — Residual scores divided by the series spread instead of the residual spread

Wrong challenge submissions the checks reject:

- `absolute_residuals` — Absolute residuals
- `centred_seasonal` — Seasonal forecast from the following week
- `fit_on_all_dates` — Model fitted on every date
- `threshold_on_test` — Threshold chosen on the test period

---

# Notebook 20 — Classical detectors: PCA/T2-Q, isolation forest, boosted trees on window features

✅ **Guided lab:** reference in [`solutions/labs/w4d2_classical_detectors/lab/`](labs/w4d2_classical_detectors/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d2_classical_detectors/challenge/`](labs/w4d2_classical_detectors/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `accepts_forbidden_columns` — No check on feature columns
- `iforest_sign` — Isolation-forest score not negated
- `iforest_unseeded` — Isolation forest without a seed
- `q_from_retained` — Q computed from the retained components
- `standardise_on_scored_rows` — Standardisation statistics taken from the rows being scored

Wrong challenge submissions the checks reject:

- `in_sample_estimate` — Estimate computed on the rows the model was fitted on
- `random_row_cv` — Out-of-fold estimate with random row folds
- `unseeded` — Models fitted without a seed
- `uses_customer_id` — customer_id used as a feature

---

# Notebook 21 — A neural comparison, where it is justified

✅ **Guided lab:** reference in [`solutions/labs/w4d3_neural_comparison/lab/`](labs/w4d3_neural_comparison/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d3_neural_comparison/challenge/`](labs/w4d3_neural_comparison/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `anomalous_rows_in_training` — anomalous rows are part of the training windows
- `centred_windows` — centred windows
- `last_epoch_weights` — the last epoch's weights are returned
- `normaliser_includes_val` — normalisation statistics include the validation frame
- `seed_not_applied` — the seed is not applied to weight initialisation

Wrong challenge submissions the checks reject:

- `ignores_seed_spread` — only the test interval enters the verdict
- `ignores_test_interval` — only seed variance enters the verdict
- `population_sd` — population standard deviation
- `single_seed_accepted` — one seed is accepted

---

# Notebook 22 — Experiment tracking and reproducibility at the experiment level

✅ **Guided lab:** reference in [`solutions/labs/w4d4_experiment_tracking/lab/`](labs/w4d4_experiment_tracking/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d4_experiment_tracking/challenge/`](labs/w4d4_experiment_tracking/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `groupby_drops_nan_keys` — configurations with missing parameters vanish
- `hash_ignores_seed` — the seed is left out of the run id
- `hash_key_order` — the hash depends on key order
- `index_read_back` — the index file is treated as the source of truth
- `partial_counted_complete` — a run is complete when metrics.json exists
- `reproduce_reads_stored` — reproduce compares the stored metrics with themselves

Wrong challenge submissions the checks reject:

- `ambiguous_filter_takes_first` — an under-specified filter silently picks one run per seed
- `difference_of_means` — difference of group means instead of mean of paired differences
- `includes_unfinished` — unfinished runs enter the comparison
- `sign_reversed` — B - A

---

# Notebook 23 — Choosing complexity on evidence

✅ **Guided lab:** reference in [`solutions/labs/w4d5_model_choice/lab/`](labs/w4d5_model_choice/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d5_model_choice/challenge/`](labs/w4d5_model_choice/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `direction_ignored` — every objective is maximised
- `leaderboard` — recommend = leaderboard
- `point_estimate_decides` — the point estimate decides
- `shallow_size` — size from sys.getsizeof
- `ties_dominate` — identical rows dominate each other
- `warmup_timed` — warm-up calls are timed

Wrong challenge submissions the checks reject:

- `customer_bootstrap` — customers resampled as if independent
- `hardcoded_budget` — decision parameters hard-coded
- `mean_latency` — mean latency against a p95 budget
- `point_estimate_switch` — switch whenever B's point estimate is ahead and fast enough

---

# Notebook 24 — Project milestone 1: evaluation report

✅ **Guided lab:** reference in [`solutions/labs/w4d6_project_milestone_1/lab/`](labs/w4d6_project_milestone_1/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w4d6_project_milestone_1/challenge/`](labs/w4d6_project_milestone_1/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `clean_deletes_raw` — clean deletes the raw data
- `number_made_in_render` — a number computed in the report step
- `phony_results` — every target is phony
- `report_recomputes` — the report step recomputes
- `results_ignore_manifest` — results do not depend on the split manifest
- `timestamp_in_provenance` — a timestamp in the provenance block

Wrong challenge submissions the checks reject:

- `dirty_commit` — the report came from a dirty working tree
- `thin_evidence` — scores without evidence
- `unticked_item` — a checklist item left unticked

---

# Notebook 25 — Research experimentation versus production inference

✅ **Guided lab:** reference in [`solutions/labs/w5d1_inference_pipeline/lab/`](labs/w5d1_inference_pipeline/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d1_inference_pipeline/challenge/`](labs/w5d1_inference_pipeline/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `all_or_nothing` — one bad run fails the whole batch
- `batch_quantile_threshold` — the threshold is re-derived from the batch
- `columns_by_position` — columns matched by position
- `ddof_one` — sample standard deviation in serving
- `rounded_output` — rounded predictions
- `timestamped_manifest` — a timestamp in the manifest
- `whole_run_normalisation` — the whole run calibrates itself

Wrong challenge submissions the checks reject:

- `burn_in_hardcoded_100` — burn-in "fixed" by changing the constant to 100
- `clip_still_missing` — two of three bugs fixed; the clip is still missing
- `report_unfilled` — code fixed, report left as the template
- `weak_parity_test` — a parity test that compares shapes, not values

---

# Notebook 26 — Model artifacts, metadata and versioning

✅ **Guided lab:** reference in [`solutions/labs/w5d2_artifacts_versioning/lab/`](labs/w5d2_artifacts_versioning/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d2_artifacts_versioning/challenge/`](labs/w5d2_artifacts_versioning/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `allow_pickle_npz` — numpy.load with allow_pickle=True
- `checksums_ignored` — checksums written but never checked on load
- `format_not_checked` — the format version is recorded but not checked
- `lexical_versions` — versions sorted as strings
- `non_atomic_promote` — the pointer is rewritten in place
- `overwrite_version` — re-registering a version replaces it
- `pickle_bundle` — the detector is pickled "for convenience"

Wrong challenge submissions the checks reject:

- `features_not_checked` — the feature layout is recorded but not checked
- `intercept_dropped` — the intercept is not saved
- `pickled_estimator` — the estimator is saved with joblib
- `policy_unfilled` — code done, policy left as the template

---

# Notebook 27 — Online inference on streams: state, warm-up and parity

✅ **Guided lab:** reference in [`solutions/labs/w5d3_online_inference/lab/`](labs/w5d3_online_inference/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d3_online_inference/challenge/`](labs/w5d3_online_inference/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `duplicate_counted_twice` — duplicate_counted_twice
- `keeps_full_history` — keeps_full_history
- `out_of_order_accepted` — out_of_order_accepted
- `restore_restarts_burn_in` — restore_restarts_burn_in
- `sample_sd_ddof1` — sample_sd_ddof1
- `warm_up_scores_zero` — warm_up_scores_zero

Wrong challenge submissions the checks reject:

- `batch_backdates` — batch_backdates
- `clear_run_not_reset` — clear_run_not_reset
- `none_counts_as_false` — none_counts_as_false
- `raises_one_early` — raises_one_early

---

# Notebook 28 — FastAPI I: endpoints, schemas and input validation

✅ **Guided lab:** reference in [`solutions/labs/w5d4_fastapi_validation/lab/`](labs/w5d4_fastapi_validation/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d4_fastapi_validation/challenge/`](labs/w5d4_fastapi_validation/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `default_validation_body` — default_validation_body
- `extra_fields_ignored` — extra_fields_ignored
- `leaks_exception_text` — leaks_exception_text
- `nan_caught_only_by_range` — nan_caught_only_by_range
- `no_range_limits` — no_range_limits
- `readyz_always_ok` — readyz_always_ok
- `reloads_model_per_request` — reloads_model_per_request

Wrong challenge submissions the checks reject:

- `auto_register` — auto_register
- `one_scorer_for_all` — one_scorer_for_all
- `out_of_order_as_422` — out_of_order_as_422
- `put_always_201` — put_always_201

---

# Notebook 29 — FastAPI II: API tests, integration tests and model lifecycle

✅ **Guided lab:** reference in [`solutions/labs/w5d5_api_testing/lab/`](labs/w5d5_api_testing/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d5_api_testing/challenge/`](labs/w5d5_api_testing/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `happy_path_only` — happy path only
- `needs_running_server` — needs a running server
- `sequential_only` — sequential only
- `status_codes_only` — status codes only

Wrong challenge submissions the checks reject:

- `no_ref_resolution` — no $ref resolution
- `paths_only` — paths only
- `symmetric_fields` — any field change is breaking

---

# Notebook 30 — Project milestone 2: packaged inference + API

✅ **Guided lab:** reference in [`solutions/labs/w5d6_project_milestone_2/lab/`](labs/w5d6_project_milestone_2/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w5d6_project_milestone_2/challenge/`](labs/w5d6_project_milestone_2/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `api_ddof_skew` — the API keeps its own copy of the formula
- `batch_global_burn_in` — one burn-in for every experiment
- `bundle_without_provenance` — a bundle without provenance
- `readme_usage_broken` — README usage out of date
- `version_not_single_sourced` — two version numbers

Wrong challenge submissions the checks reject:

- `evidence_too_short` — a score without evidence
- `no_tag` — no release tag
- `placeholders_left` — a TODO left in place
- `unticked_item` — an unticked checklist item

---

# Notebook 31 — Docker I: images, layers and a correct Dockerfile

✅ **Guided lab:** reference in [`solutions/labs/w6d1_docker_basics/lab/`](labs/w6d1_docker_basics/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d1_docker_basics/challenge/`](labs/w6d1_docker_basics/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `binds_container_loopback` — binds_container_loopback
- `copy_all_before_install` — copy_all_before_install
- `curl_healthcheck_without_curl` — curl_healthcheck_without_curl
- `gitignore_style_dockerignore` — gitignore_style_dockerignore
- `publishes_all_interfaces` — publishes_all_interfaces
- `runs_as_root` — runs_as_root
- `shell_form_cmd` — shell_form_cmd
- `wrong_model_dir` — wrong_model_dir

Wrong challenge submissions the checks reject:

- `a_unchanged` — a_unchanged
- `b_shell_wrapper_without_exec` — b_shell_wrapper_without_exec
- `b_user_only` — b_user_only
- `c_excludes_models` — c_excludes_models
- `c_gitignore_style` — c_gitignore_style

---

# Notebook 32 — Docker II: pinned dependencies, multi-stage builds, smoke tests

✅ **Guided lab:** reference in [`solutions/labs/w6d2_docker_reproducibility/lab/`](labs/w6d2_docker_reproducibility/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d2_docker_reproducibility/challenge/`](labs/w6d2_docker_reproducibility/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `compilers_in_runtime` — compilers_in_runtime
- `lock_top_level_only` — lock_top_level_only
- `lock_without_hashes` — lock_without_hashes
- `single_stage` — single_stage
- `smoke_checks_status_only` — smoke_checks_status_only
- `smoke_no_wait` — smoke_no_wait
- `tag_not_digest` — tag_not_digest

Wrong challenge submissions the checks reject:

- `build_still_resolves_in` — build_still_resolves_in
- `pin_latest` — pin_latest
- `pin_without_hash` — pin_without_hash
- `range_with_hash` — range_with_hash
- `wrong_hash` — wrong_hash

---

# Notebook 33 — Continuous integration with GitHub Actions

✅ **Guided lab:** reference in [`solutions/labs/w6d3_ci/lab/`](labs/w6d3_ci/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d3_ci/challenge/`](labs/w6d3_ci/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `evaluation_in_push_gate` — the real-data evaluation runs on every push
- `floating_action_ref` — an action pinned to a branch
- `image_without_needs` — the image job has no `needs`
- `python_versions_unquoted` — unquoted Python versions in the matrix
- `secret_in_run` — a secret interpolated into a run script
- `write_all_permissions` — permissions: write-all

Wrong challenge submissions the checks reject:

- `cache_key_run_id` — hashFiles added, but the key still ends in a per-run value
- `perf_marked_not_excluded` — the test is marked perf but the default run still includes it
- `threshold_raised` — the timing budget raised tenfold
- `wget_instead_of_curl` — curl swapped for wget inside the container

---

# Notebook 34 — Latency, throughput and resource use

✅ **Guided lab:** reference in [`solutions/labs/w6d4_latency_resources/lab/`](labs/w6d4_latency_resources/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d4_latency_resources/challenge/`](labs/w6d4_latency_resources/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `budget_strict_less_than` — the limit itself fails the budget
- `closed_loop` — closed loop
- `errors_in_latency` — failed requests included in the latency percentiles
- `latency_from_actual_send` — latency measured from the actual send (coordinated omission)
- `percentile_nearest_rank` — index-based percentile without interpolation

Wrong challenge submissions the checks reject:

- `best_passing_rate` — takes the highest passing rate anywhere on the curve
- `ignores_utilisation` — sizes for 100 % utilisation
- `milliseconds_not_converted` — Little's law with W in milliseconds
- `rounds_to_nearest` — rounds to the nearest worker instead of up

---

# Notebook 35 — One small cloud deployment on AWS (authorisation-gated)

✅ **Guided lab:** reference in [`solutions/labs/w6d5_cloud_deployment/lab/`](labs/w6d5_cloud_deployment/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d5_cloud_deployment/challenge/`](labs/w6d5_cloud_deployment/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `live_gate_is_only_the_flag` — live_gate_is_only_the_flag
- `mutable_latest_tag` — mutable_latest_tag
- `public_by_default` — public_by_default
- `taskdef_without_health_or_logs` — taskdef_without_health_or_logs
- `teardown_forgets_logs_and_role` — teardown_forgets_logs_and_role

Wrong challenge submissions the checks reject:

- `keys_kept_but_rotated` — keys_kept_but_rotated
- `office_range_open` — office_range_open
- `still_latest` — still_latest
- `teardown_forgets_bucket` — teardown_forgets_bucket

---

# Notebook 36 — Delivery and operational debugging; project milestone 3

✅ **Guided lab:** reference in [`solutions/labs/w6d6_cd_ops_debugging/lab/`](labs/w6d6_cd_ops_debugging/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w6d6_cd_ops_debugging/challenge/`](labs/w6d6_cd_ops_debugging/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `debug_log_two_incidents` — debug_log_two_incidents
- `rollback_by_list_position` — rollback_by_list_position
- `rollback_by_tag` — rollback_by_tag
- `rollback_to_running_image` — rollback_to_running_image
- `settings_accept_unknown_vars` — settings_accept_unknown_vars
- `settings_vague_errors` — settings_vague_errors

Wrong challenge submissions the checks reject:

- `action_items_without_owners` — action_items_without_owners
- `blames_the_deployer` — blames_the_deployer
- `impact_from_detection` — impact_from_detection
- `invented_times` — invented_times

---

# Notebook 37 — Structured logging and service metrics

✅ **Guided lab:** reference in [`solutions/labs/w7d1_service_logging_metrics/lab/`](labs/w7d1_service_logging_metrics/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d1_service_logging_metrics/challenge/`](labs/w7d1_service_logging_metrics/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `histogram_not_cumulative` — per-bucket counts instead of cumulative
- `inflight_leak_on_error` — in-flight gauge decremented only on success
- `logquery_crashes_on_junk` — query tool assumes every line is JSON
- `logs_raw_payload` — logs the full request payload
- `no_finally_on_error` — bookkeeping only on the success path
- `request_id_ignored` — incoming request id ignored
- `route_label_raw_path` — raw path as the route label

Wrong challenge submissions the checks reject:

- `burn_rate_divides_by_target` — burn rate divided by the target instead of the error budget
- `client_errors_count_as_bad` — 4xx counted against availability
- `latency_includes_errors` — errors included in the latency SLI
- `short_window_only` — pages on the short window alone

---

# Notebook 38 — Input monitoring and drift statistics

✅ **Guided lab:** reference in [`solutions/labs/w7d2_input_monitoring_drift/lab/`](labs/w7d2_input_monitoring_drift/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d2_input_monitoring_drift/challenge/`](labs/w7d2_input_monitoring_drift/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `ks_at_reference_points_only` — KS evaluated only at the reference's points
- `missing_counted_as_violation` — NaN treated as a schema violation
- `no_multiple_testing_correction` — each sensor calibrated to the target rate on its own
- `psi_without_floor` — PSI without the epsilon floor
- `violations_reach_statistics` — only infinities count as violations
- `w1_on_sorted_pairs` — W1 as the mean gap between sorted values, truncated to the shorter sample

Wrong challenge submissions the checks reject:

- `calendar_ignored` — change calendar ignored
- `folklore_psi_threshold` — the folklore rule PSI > 0.25 instead of a calibrated threshold
- `missing_ignored` — missingness not monitored
- `suppressed_forever` — a planned change silences the feature for good

---

# Notebook 39 — Drift is not degradation: delayed labels and measured performance

✅ **Guided lab:** reference in [`solutions/labs/w7d3_drift_vs_degradation/lab/`](labs/w7d3_drift_vs_degradation/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d3_drift_vs_degradation/challenge/`](labs/w7d3_drift_vs_degradation/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `drift_decides_model_health` — drift_decides_model_health
- `earliest_verdict_wins` — earliest_verdict_wins
- `ignores_as_of` — ignores_as_of
- `insufficient_reported_as_zero` — insufficient_reported_as_zero
- `pending_counted_as_false` — pending_counted_as_false

Wrong challenge submissions the checks reject:

- `evaluated_before_labels_arrive` — evaluated_before_labels_arrive
- `fixed_drift_threshold` — fixed_drift_threshold
- `recall_without_missed_fault_source` — recall_without_missed_fault_source
- `retrain_on_drift` — retrain_on_drift
- `window_too_short` — window_too_short

---

# Notebook 40 — Model updates: retraining triggers, shadow and canary, rollback

✅ **Guided lab:** reference in [`solutions/labs/w7d4_model_updates_rollback/lab/`](labs/w7d4_model_updates_rollback/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d4_model_updates_rollback/challenge/`](labs/w7d4_model_updates_rollback/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `audit_before_move` — audit_before_move
- `no_compatibility_check` — no_compatibility_check
- `pointer_written_in_place` — pointer_written_in_place
- `policy_ignored` — policy_ignored
- `rollback_toggles_last_move` — rollback_toggles_last_move
- `shadow_candidate_first_on_same_frame` — shadow_candidate_first_on_same_frame
- `shadow_errors_propagate` — shadow_errors_propagate
- `unpaired_gate` — unpaired_gate

Wrong challenge submissions the checks reject:

- `control_ignored` — control_ignored
- `evaluated_only_at_the_end` — evaluated_only_at_the_end
- `no_minimum_exposure` — no_minimum_exposure
- `point_estimates_only` — point_estimates_only

---

# Notebook 41 — Reliability and failure handling

✅ **Guided lab:** reference in [`solutions/labs/w7d5_reliability/lab/`](labs/w7d5_reliability/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d5_reliability/challenge/`](labs/w7d5_reliability/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `happy_path_drills` — happy_path_drills
- `ignores_retry_after` — ignores_retry_after
- `nan_passthrough` — nan_passthrough
- `new_key_per_attempt` — new_key_per_attempt
- `no_jitter` — no_jitter
- `ready_when_degraded` — ready_when_degraded
- `retries_client_errors` — retries_client_errors
- `silent_degradation` — silent_degradation
- `slot_released_on_response` — slot_released_on_response

Wrong challenge submissions the checks reject:

- `counts_total_failures` — counts_total_failures
- `duplicate_is_out_of_order` — duplicate_is_out_of_order
- `never_half_opens` — never_half_opens
- `no_stream_failures` — no_stream_failures

---

# Notebook 42 — Project milestone 4: monitoring demonstration and runbook

✅ **Guided lab:** reference in [`solutions/labs/w7d6_project_milestone_4/lab/`](labs/w7d6_project_milestone_4/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w7d6_project_milestone_4/challenge/`](labs/w7d6_project_milestone_4/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `rollback_without_restart` — rollback_without_restart
- `runbook_missing_alert` — runbook_missing_alert
- `server_left_running` — server_left_running
- `stale_report_number` — stale_report_number
- `timeline_omits_quiet_events` — timeline_omits_quiet_events

Wrong challenge submissions the checks reject:

- `evidence_too_short` — evidence_too_short
- `hides_the_miss` — hides_the_miss
- `placeholders_left` — placeholders_left
- `unticked_item` — unticked_item

---

# Notebook 43 — Project completion audit: reproduce from a clean clone

✅ **Guided lab:** reference in [`solutions/labs/w8d1_project_completion/lab/`](labs/w8d1_project_completion/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w8d1_project_completion/challenge/`](labs/w8d1_project_completion/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `accepts_lower_bounds` — accepts_lower_bounds
- `copies_working_tree` — copies_working_tree
- `deliverables_todo` — deliverables_todo
- `ignores_repeat` — ignores_repeat
- `relative_tolerance` — relative_tolerance
- `runs_in_source` — runs_in_source
- `system_site_packages` — system_site_packages

Wrong challenge submissions the checks reject:

- `everything_fix_now` — everything_fix_now
- `over_budget` — over_budget
- `placeholders_left` — placeholders_left
- `reasons_missing` — reasons_missing

---

# Notebook 44 — Technical report and model limitations

✅ **Guided lab:** reference in [`solutions/labs/w8d2_report_limitations/lab/`](labs/w8d2_report_limitations/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w8d2_report_limitations/challenge/`](labs/w8d2_report_limitations/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `code_spans_checked` — code_spans_checked
- `exact_string_match` — exact_string_match
- `limitations_count_only` — limitations_count_only
- `percent_not_scaled` — percent_not_scaled
- `sentence_end_skipped` — sentence_end_skipped
- `significance_always` — significance_always
- `unit_anywhere` — unit_anywhere

Wrong challenge submissions the checks reject:

- `no_line_numbers` — no_line_numbers
- `placeholders_left` — placeholders_left
- `surface_issues_only` — surface_issues_only
- `vague_changes` — vague_changes

---

# Notebook 45 — ML system design

✅ **Guided lab:** reference in [`solutions/labs/w8d3_system_design/lab/`](labs/w8d3_system_design/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w8d3_system_design/challenge/`](labs/w8d3_system_design/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `delay_ignored` — delay_ignored
- `half_width_not_squared` — half_width_not_squared
- `no_utilisation_headroom` — no_utilisation_headroom
- `per_hour_qps` — per_hour_qps
- `replicas_rounded` — replicas_rounded
- `replication_ignored` — replication_ignored
- `silent_negative_latency` — silent_negative_latency

Wrong challenge submissions the checks reject:

- `approves` — approves
- `misses_leak` — misses_leak
- `no_blockers` — no_blockers
- `skips_serving` — skips_serving
- `vague_fixes` — vague_fixes

---

# Notebook 46 — Coding and SQL interviews, timed

✅ **Guided lab:** reference in [`solutions/labs/w8d4_coding_interviews/lab/`](labs/w8d4_coding_interviews/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w8d4_coding_interviews/challenge/`](labs/w8d4_coding_interviews/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `p1_counts_changed_minds` — p1_counts_changed_minds
- `p2_alarm_reused` — p2_alarm_reused
- `p2_nested_loops` — p2_nested_loops
- `p3_window_from_last_seen` — p3_window_from_last_seen
- `p4_naive_sum_of_squares` — p4_naive_sum_of_squares
- `p4_sample_variance` — p4_sample_variance
- `p5_greedy_average` — p5_greedy_average
- `p6_no_cycle_check` — p6_no_cycle_check
- `p6_recursive_dfs` — p6_recursive_dfs
- `q1_fanout_count` — q1_fanout_count
- `q1_inner_join_drops_city` — q1_inner_join_drops_city
- `q2_all_statuses` — q2_all_statuses
- `q2_rank_keeps_ties` — q2_rank_keeps_ties
- `q3_latest_tie` — q3_latest_tie
- `q3_trips_not_days` — q3_trips_not_days

Wrong challenge submissions the checks reject:

- `c1_adjacent_differences` — c1_adjacent_differences
- `c1_quadratic` — c1_quadratic
- `c2_calendar_month` — c2_calendar_month
- `c2_first_trip_any_status` — c2_first_trip_any_status
- `c2_integer_division` — c2_integer_division

---

# Notebook 47 — Explaining the project and defending tradeoffs

✅ **Guided lab:** reference in [`solutions/labs/w8d5_project_explanation/lab/`](labs/w8d5_project_explanation/lab/) — executed; passes its checks.

✅ **Independent challenge:** reference in [`solutions/labs/w8d5_project_explanation/challenge/`](labs/w8d5_project_explanation/challenge/) — executed; passes its checks.


Wrong lab submissions the checks reject:

- `answer_too_long` — answer_too_long
- `dead_artifact_path` — dead_artifact_path
- `missing_question` — missing_question
- `placeholder_left` — placeholder_left
- `script_missing_limitation` — script_missing_limitation

Wrong challenge submissions the checks reject:

- `adversarial_missing_redirect` — adversarial_missing_redirect
- `no_translation_section` — no_translation_section
- `numbers_without_uncertainty` — numbers_without_uncertainty
- `template_placeholder_left` — template_placeholder_left

---

# Notebook 48 — Final independent assessment


---

