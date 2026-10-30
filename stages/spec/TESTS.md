# Проверки S0–S7

Дата UTC: 2026-10-30T14:05:35.537916+00:00. Python 3.12.14.

Итог: **passed**, тестов: **108**.

Тесты работают с фейками; настоящие вызовы модели приведены отдельно в EVAL.md.

| Проверка | Тестов | Код выхода |
|---|---:|---:|
| `.venv/bin/python -m unittest discover -s stages/analysis/tests -v` | 24 | 0 |
| `.venv/bin/python -m unittest discover -s stages/spec/tests -v` | 51 | 0 |
| `.venv/bin/python -m unittest discover -s gates/tests -v` | 33 | 0 |
| `.venv/bin/python -m contracts.export` | — | 0 |
| `.venv/bin/python -m compileall -q contracts stages/analysis stages/spec gates` | — | 0 |
| `.venv/bin/python -m pip check` | — | 0 |

## .venv/bin/python -m unittest discover -s stages/analysis/tests -v

```text
test_a1_checkpoint_resumes_without_reextracting (test_analysis_stage.AnalysisStageTests.test_a1_checkpoint_resumes_without_reextracting) ... ok
test_a2_completes_with_defaults_and_no_sandbox (test_analysis_stage.AnalysisStageTests.test_a2_completes_with_defaults_and_no_sandbox) ... ok
test_bad_issue_action_is_an_explicit_unresolved_assumption (test_analysis_stage.AnalysisStageTests.test_bad_issue_action_is_an_explicit_unresolved_assumption) ... ok
test_budget_exhaustion_preserves_schema_valid_partial_artifact (test_analysis_stage.AnalysisStageTests.test_budget_exhaustion_preserves_schema_valid_partial_artifact) ... ok
test_common_gherkin_keyword_formatting_is_normalized (test_analysis_stage.AnalysisStageTests.test_common_gherkin_keyword_formatting_is_normalized) ... ok
test_duplicate_requirements_are_merged_by_normalized_text (test_analysis_stage.AnalysisStageTests.test_duplicate_requirements_are_merged_by_normalized_text) ... ok
test_invalid_quote_is_repaired_as_targeted_patch (test_analysis_stage.AnalysisStageTests.test_invalid_quote_is_repaired_as_targeted_patch) ... ok
test_malformed_response_is_contract_error (test_analysis_stage.AnalysisStageTests.test_malformed_response_is_contract_error) ... ok
test_oversized_item_is_a_resource_limit_before_model_call (test_analysis_stage.AnalysisStageTests.test_oversized_item_is_a_resource_limit_before_model_call) ... ok
test_partial_answers_remain_waiting (test_analysis_stage.AnalysisStageTests.test_partial_answers_remain_waiting) ... ok
test_questions_cap_preserves_overflow_as_a_traced_assumption (test_analysis_stage.AnalysisStageTests.test_questions_cap_preserves_overflow_as_a_traced_assumption) ... ok
test_repair_cannot_change_unrelated_fields (test_analysis_stage.AnalysisStageTests.test_repair_cannot_change_unrelated_fields) ... ok
test_revision_is_bounded_and_unsolved_quote_is_flagged (test_analysis_stage.AnalysisStageTests.test_revision_is_bounded_and_unsolved_quote_is_flagged) ... ok
test_role_labels_are_resolved_to_declared_ids (test_analysis_stage.AnalysisStageTests.test_role_labels_are_resolved_to_declared_ids) ... ok
test_stale_answers_after_source_change_are_rejected (test_analysis_stage.AnalysisStageTests.test_stale_answers_after_source_change_are_rejected) ... ok
test_window_splitting_and_delimiter_injection (test_analysis_stage.AnalysisStageTests.test_window_splitting_and_delimiter_injection) ... ok
test_csv_delimiter_and_inconsistent_types (test_inputs.InputTests.test_csv_delimiter_and_inconsistent_types) ... ok
test_docx_paragraphs_and_table (test_inputs.InputTests.test_docx_paragraphs_and_table) ... ok
test_geojson_line_is_not_invented_polygon (test_inputs.InputTests.test_geojson_line_is_not_invented_polygon) ... ok
test_image_missing_and_malformed_files (test_inputs.InputTests.test_image_missing_and_malformed_files) ... ok
test_outside_input_and_symlink_are_rejected (test_inputs.InputTests.test_outside_input_and_symlink_are_rejected) ... ok
test_pdf_text_and_image_slide (test_inputs.InputTests.test_pdf_text_and_image_slide) ... ok
test_profile_json_fields_dates_anomalies_and_three_samples (test_inputs.InputTests.test_profile_json_fields_dates_anomalies_and_three_samples) ... ok
test_text_markdown_stable_fragments (test_inputs.InputTests.test_text_markdown_stable_fragments) ... ok

----------------------------------------------------------------------
Ran 24 tests in 0.683s

OK
```

## .venv/bin/python -m unittest discover -s stages/spec/tests -v

```text
test_all_identified_lists_reject_duplicates (test_contracts.AnalysisTests.test_all_identified_lists_reject_duplicates) ... ok
test_data_card_schema_alias_round_trip (test_contracts.AnalysisTests.test_data_card_schema_alias_round_trip) ... ok
test_extra_field_rejected_at_root_and_nested_model (test_contracts.AnalysisTests.test_extra_field_rejected_at_root_and_nested_model) ... ok
test_fixture_and_serialization (test_contracts.AnalysisTests.test_fixture_and_serialization) ... ok
test_lists_without_id_do_not_require_invented_ids (test_contracts.AnalysisTests.test_lists_without_id_do_not_require_invented_ids) ... ok
test_question_default_and_answer_author (test_contracts.AnalysisTests.test_question_default_and_answer_author) ... ok
test_schema_version_required_and_closed (test_contracts.AnalysisTests.test_schema_version_required_and_closed) ... ok
test_source_fragments_and_quotes_match_original (test_contracts.AnalysisTests.test_source_fragments_and_quotes_match_original) ... ok
test_unknown_requirement_type_characteristic_module_platform (test_contracts.AnalysisTests.test_unknown_requirement_type_characteristic_module_platform) ... ok
test_closed_vocabularies (test_contracts.AppTests.test_closed_vocabularies) ... ok
test_every_section_has_an_independent_model (test_contracts.AppTests.test_every_section_has_an_independent_model) ... ok
test_fixture_and_alias_round_trip (test_contracts.AppTests.test_fixture_and_alias_round_trip) ... ok
test_fixture_references_resolve (test_contracts.AppTests.test_fixture_references_resolve) ... ok
test_nested_extra_fields_rejected (test_contracts.AppTests.test_nested_extra_fields_rejected) ... ok
test_no_crud_or_generated_events_written (test_contracts.AppTests.test_no_crud_or_generated_events_written) ... ok
test_semantic_violations_remain_available_to_g1 (test_contracts.AppTests.test_semantic_violations_remain_available_to_g1) ... ok
test_trigger_closed_and_single_kind (test_contracts.AppTests.test_trigger_closed_and_single_kind) ... ok
test_alias_paths_are_equivalent (test_contracts.DependentsTests.test_alias_paths_are_equivalent) ... ok
test_analysis_trace_paths (test_contracts.DependentsTests.test_analysis_trace_paths) ... ok
test_cycles_terminate_and_do_not_mutate_app (test_contracts.DependentsTests.test_cycles_terminate_and_do_not_mutate_app) ... ok
test_declared_event_to_notification (test_contracts.DependentsTests.test_declared_event_to_notification) ... ok
test_enum_reference (test_contracts.DependentsTests.test_enum_reference) ... ok
test_event_and_schedule_triggers (test_contracts.DependentsTests.test_event_and_schedule_triggers) ... ok
test_field_to_query_hook_and_seed (test_contracts.DependentsTests.test_field_to_query_hook_and_seed) ... ok
test_opaque_sections_retain_explicit_links (test_contracts.DependentsTests.test_opaque_sections_retain_explicit_links) ... ok
test_parameter_to_hook_to_field_to_timer_to_notification (test_contracts.DependentsTests.test_parameter_to_hook_to_field_to_timer_to_notification) ... ok
test_query_select_and_input_reference (test_contracts.DependentsTests.test_query_select_and_input_reference) ... ok
test_role_command_permissions_and_transition (test_contracts.DependentsTests.test_role_command_permissions_and_transition) ... ok
test_similar_identifiers_do_not_match (test_contracts.DependentsTests.test_similar_identifiers_do_not_match) ... ok
test_transition_effect_and_state_index (test_contracts.DependentsTests.test_transition_effect_and_state_index) ... ok
test_unrelated_entity_is_not_affected (test_contracts.DependentsTests.test_unrelated_entity_is_not_affected) ... ok
test_checked_in_schemas_are_current (test_contracts.ExportTests.test_checked_in_schemas_are_current) ... ok
test_schema_export_is_deterministic_and_uses_wire_aliases (test_contracts.ExportTests.test_schema_export_is_deterministic_and_uses_wire_aliases) ... ok
test_both_domains_recorded_pass_end_to_end (test_eval.EvalTests.test_both_domains_recorded_pass_end_to_end) ... ok
test_gateway_enforces_budget_before_call (test_eval.EvalTests.test_gateway_enforces_budget_before_call) ... ok
test_gateway_is_stateless_and_records_actual_usage (test_eval.EvalTests.test_gateway_is_stateless_and_records_actual_usage) ... ok
test_gateway_rejects_model_substitution (test_eval.EvalTests.test_gateway_rejects_model_substitution) ... ok
test_gateway_reserves_input_tokens_in_budget (test_eval.EvalTests.test_gateway_reserves_input_tokens_in_budget) ... ok
test_missing_case_is_not_reported_as_success (test_eval.EvalTests.test_missing_case_is_not_reported_as_success) ... ok
test_prompt_changes_require_a_new_recorded_eval (test_eval.EvalTests.test_prompt_changes_require_a_new_recorded_eval) ... ok
test_repair_continuation_preserves_prior_failure_and_spend (test_eval.EvalTests.test_repair_continuation_preserves_prior_failure_and_spend) ... ok
test_unrelated_contract_errors_cannot_be_promoted_by_continuation (test_eval.EvalTests.test_unrelated_contract_errors_cannot_be_promoted_by_continuation) ... ok
test_addressed_repair_fixes_unreachable_state (test_spec_stage.SpecStageTests.test_addressed_repair_fixes_unreachable_state) ... ok
test_bad_contract_cannot_be_repaired_silently (test_spec_stage.SpecStageTests.test_bad_contract_cannot_be_repaired_silently) ... ok
test_patch_cannot_rename_stable_ids (test_spec_stage.SpecStageTests.test_patch_cannot_rename_stable_ids) ... ok
test_patch_rejects_outside_changes_and_document_is_unchanged (test_spec_stage.SpecStageTests.test_patch_rejects_outside_changes_and_document_is_unchanged) ... ok
test_patch_test_copy_move_and_pointer_escaping (test_spec_stage.SpecStageTests.test_patch_test_copy_move_and_pointer_escaping) ... ok
test_repair_context_limit_preserves_valid_artifacts (test_spec_stage.SpecStageTests.test_repair_context_limit_preserves_valid_artifacts) ... ok
test_spec_budget_creates_partial_app (test_spec_stage.SpecStageTests.test_spec_budget_creates_partial_app) ... ok
test_spec_seven_steps_seventeen_sections (test_spec_stage.SpecStageTests.test_spec_seven_steps_seventeen_sections) ... ok
test_whole_section_replacement_rejected (test_spec_stage.SpecStageTests.test_whole_section_replacement_rejected) ... ok

----------------------------------------------------------------------
Ran 51 tests in 0.397s

OK
```

## .venv/bin/python -m unittest discover -s gates/tests -v

```text
test_ac_not_testable (test_gates.GateTests.test_ac_not_testable) ... ok
test_boundary_numbers_outside_examples_do_not_count (test_gates.GateTests.test_boundary_numbers_outside_examples_do_not_count) ... ok
test_br_no_ac (test_gates.GateTests.test_br_no_ac) ... ok
test_br_no_boundary (test_gates.GateTests.test_br_no_boundary) ... ok
test_br_no_hook (test_gates.GateTests.test_br_no_hook) ... ok
test_check_does_not_write_to_workspace (test_gates.GateTests.test_check_does_not_write_to_workspace) ... ok
test_clean_fixture_passes_both_gates (test_gates.GateTests.test_clean_fixture_passes_both_gates) ... ok
test_contract_analysis (test_gates.GateTests.test_contract_analysis) ... ok
test_contract_app (test_gates.GateTests.test_contract_app) ... ok
test_data_mapping_requires_known_field_and_units (test_gates.GateTests.test_data_mapping_requires_known_field_and_units) ... ok
test_data_unknown_field (test_gates.GateTests.test_data_unknown_field) ... ok
test_duration_boundaries_use_explicit_example_units (test_gates.GateTests.test_duration_boundaries_use_explicit_example_units) ... ok
test_evt_incomplete (test_gates.GateTests.test_evt_incomplete) ... ok
test_hook_must_trace_its_own_rule_acceptance (test_gates.GateTests.test_hook_must_trace_its_own_rule_acceptance) ... ok
test_in_unparsed (test_gates.GateTests.test_in_unparsed) ... ok
test_nfr_not_measurable (test_gates.GateTests.test_nfr_not_measurable) ... ok
test_noise_is_not_uncovered (test_gates.GateTests.test_noise_is_not_uncovered) ... ok
test_ntf_bad_event (test_gates.GateTests.test_ntf_bad_event) ... ok
test_outline_result_is_checked_after_example_substitution (test_gates.GateTests.test_outline_result_is_checked_after_example_substitution) ... ok
test_param_literal (test_gates.GateTests.test_param_literal) ... ok
test_rbac_orphan (test_gates.GateTests.test_rbac_orphan) ... ok
test_ref_unresolved (test_gates.GateTests.test_ref_unresolved) ... ok
test_req_no_quote (test_gates.GateTests.test_req_no_quote) ... ok
test_req_uncovered (test_gates.GateTests.test_req_uncovered) ... ok
test_sm_deadlock (test_gates.GateTests.test_sm_deadlock) ... ok
test_sm_guard_overlap (test_gates.GateTests.test_sm_guard_overlap) ... ok
test_sm_no_trigger (test_gates.GateTests.test_sm_no_trigger) ... ok
test_sm_unreachable (test_gates.GateTests.test_sm_unreachable) ... ok
test_sources_cannot_be_fabricated_to_justify_quote (test_gates.GateTests.test_sources_cannot_be_fabricated_to_justify_quote) ... ok
test_src_uncovered (test_gates.GateTests.test_src_uncovered) ... ok
test_then_conjunction_may_contain_the_observable_result (test_gates.GateTests.test_then_conjunction_may_contain_the_observable_result) ... ok
test_us_no_endpoint (test_gates.GateTests.test_us_no_endpoint) ... ok
test_vague_word (test_gates.GateTests.test_vague_word) ... ok

----------------------------------------------------------------------
Ran 33 tests in 0.040s

OK
```

## .venv/bin/python -m contracts.export

```text
contracts/schemas/analysis.schema.json
contracts/schemas/app.schema.json
```

## .venv/bin/python -m compileall -q contracts stages/analysis stages/spec gates

```text

```

## .venv/bin/python -m pip check

```text
No broken requirements found.
```
