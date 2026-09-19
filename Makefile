PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
export PYTHONPATH := $(CURDIR)/inference-runtime/src:$(PYTHONPATH)

.PHONY: check test assessment-check boosted-comparison-check boundary-check contract-test dataset-check feature-diagnostics-check feature-pipeline-check inference-runtime-check leakage-check logistic-baseline-check observation-check streaming-check streaming-integration-check p4-02-check p4-02-integration-check p4-03-check r2-08-design-check r2-12-diagnostic-contract-check r2-13-diagnostic-readiness-check r2-14-qualification-check r2-14a-diagnostic-contract-check r2-14b-diagnostic-check r2-14ba-diagnostic-contract-check r2-14bb-diagnostic-contract-check r2-14c-contract-check r2-14d-qualification-check v6-evaluation-check v6-acceptance-check scoring-authorization-check simulator-test temporal-split-check v2-acceptance-check v2-corpus-check v2-evaluation-check v3-acceptance-check v3-corpus-check v3-evaluation-check serve-roadmap run-dashboard check-contracts check-v1-v3 check-v4-v5 probability-calibration-check model-explanations-check model-bundle-check final-evaluation-check rules-eligibility-check optimization-check serving-gateway-check assistant-check dashboard-check dashboard-app-test phase-03-qualification-check

.PHONY: read-only-qualification-check read-only-artifact-checks ci-read-only-qualification-check rh12-evidence-check

rh12-evidence-check:
	$(PYTHON) scripts/run_rh_12_evidence_reconciliation.py --check

serve-roadmap:
	$(PYTHON) scripts/serve_roadmap.py

run-dashboard:
	PYTHONPATH=$(CURDIR)/inference-runtime/src:. $(PYTHON) -m streamlit run dashboard/app.py

check: check-contracts inference-runtime-check check-v1-v3 check-v4-v5 probability-calibration-check model-explanations-check model-bundle-check final-evaluation-check rules-eligibility-check optimization-check serving-gateway-check assistant-check dashboard-check phase-03-qualification-check simulator-test

read-only-qualification-check:
	bash scripts/verify_read_only.sh make check

# CI runs the checks that materialize or verify published artifacts here;
# contract, unit, runtime, serving, and dashboard coverage runs in parallel
# jobs above and does not need to be repeated in this read-only gate.
read-only-artifact-checks:
	$(PYTHON) scripts/run_probability_calibration.py --check
	$(PYTHON) scripts/run_model_explanations.py --check
	$(PYTHON) scripts/run_model_bundle.py --check
	$(PYTHON) scripts/run_final_evaluation.py --check
	$(PYTHON) scripts/run_phase_03_qualification.py --check

ci-read-only-qualification-check:
	bash scripts/verify_read_only.sh make read-only-artifact-checks

inference-runtime-check:
	$(PYTHON) -m unittest discover -s inference-runtime/tests -p 'test_*.py' -v

dashboard-check:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m unittest dashboard.tests.test_dashboard_services dashboard.tests.test_dashboard_smoke -v

dashboard-app-test:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m unittest discover -s dashboard/tests -p 'test_dashboard_app_test.py' -v

phase-03-qualification-check:
	$(PYTHON) scripts/run_phase_03_qualification.py --check
	$(PYTHON) -m unittest simulator.tests.test_phase_03_qualification -v

rules-eligibility-check:
	$(PYTHON) -m unittest simulator.tests.test_rules_eligibility -v

optimization-check:
	$(PYTHON) -m unittest simulator.tests.test_optimization -v

serving-gateway-check:
	$(PYTHON) -m unittest discover -s serving/tests -p 'test_*.py' -v

assistant-check:
	$(PYTHON) -m unittest simulator.tests.test_assistant -v

check-contracts: boundary-check dataset-check contract-test streaming-check r2-08-design-check r2-12-diagnostic-contract-check r2-14a-diagnostic-contract-check r2-14ba-diagnostic-contract-check r2-14c-contract-check

streaming-check:
	PYTHONPATH=$(CURDIR)/simulator/src:$(CURDIR) $(PYTHON) -m unittest simulator.tests.test_streaming simulator.tests.test_kafka_adapter -v

streaming-integration-check:
	INFORSIGHT_RUN_KAFKA_INTEGRATION=1 PYTHONPATH=$(CURDIR)/simulator/src:$(CURDIR) $(PYTHON) -m unittest simulator.tests.test_kafka_integration -v

# Focused P4-02 checks. The integration variant requires the optional
# simulator[integration] extra and a reachable Docker daemon.
p4-02-check: streaming-check

p4-02-integration-check: p4-02-check streaming-integration-check

# Focused P4-03 Java control-plane checks.
.PHONY: p4-03-integration-check
p4-03-check:
	mvn -f services/control-plane/pom.xml test

p4-03-integration-check:
	INFORSIGHT_RUN_JAVA_INTEGRATION=1 mvn -f services/control-plane/pom.xml test

check-v1-v3: assessment-check observation-check temporal-split-check feature-pipeline-check logistic-baseline-check boosted-comparison-check feature-diagnostics-check scoring-authorization-check leakage-check v2-corpus-check v2-evaluation-check v2-acceptance-check v3-corpus-check v3-evaluation-check v3-acceptance-check

check-v4-v5: r2-13-diagnostic-readiness-check r2-14-qualification-check r2-14b-diagnostic-check r2-14bb-diagnostic-check r2-14d-qualification-check v6-evaluation-check v6-acceptance-check

final-evaluation-check:
	$(PYTHON) scripts/run_final_evaluation.py --check
	$(PYTHON) -m unittest simulator.tests.test_final_evaluation -v

model-bundle-check:
	$(PYTHON) scripts/run_model_bundle.py --check
	$(PYTHON) -m unittest simulator.tests.test_model_bundle -v

model-explanations-check:
	$(PYTHON) scripts/run_model_explanations.py --check
	$(PYTHON) -m unittest simulator.tests.test_model_explanations -v

probability-calibration-check:
	$(PYTHON) scripts/run_probability_calibration.py --check
	$(PYTHON) -m unittest simulator.tests.test_probability_calibration -v

v6-acceptance-check:
	$(PYTHON) scripts/run_v6_statistical_acceptance.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v6_statistical_acceptance.py --check
	$(PYTHON) -m unittest simulator.tests.test_v6_acceptance -v

v6-evaluation-check:
	$(PYTHON) scripts/check_v6_evaluation_support.py --check
	$(PYTHON) scripts/build_v6_evaluation_pipeline.py --check
	$(PYTHON) -m unittest simulator.tests.test_v6_evaluation -v

r2-14d-qualification-check:
	$(PYTHON) scripts/run_v6_qualification.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v6_qualification.py --check
	$(PYTHON) -m unittest simulator.tests.test_v6_config simulator.tests.test_v6_corpus simulator.tests.test_v6_qualification -v

r2-14c-contract-check:
	$(PYTHON) scripts/check_r2_14c_v6_contract.py
	$(PYTHON) -m unittest simulator.tests.test_v6_contract -v

r2-14bb-diagnostic-check:
	$(PYTHON) scripts/run_v5_redesign_diagnostics_execution.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v5_redesign_diagnostics_execution.py --check
	$(PYTHON) -m unittest simulator.tests.test_v5_diagnostics_execution -v

r2-14ba-diagnostic-contract-check:
	$(PYTHON) scripts/check_r2_14ba_diagnostic_contract.py
	$(PYTHON) -m unittest simulator.tests.test_v5_diagnostic_contract_amendment -v

r2-14b-diagnostic-check:
	! $(PYTHON) scripts/run_v5_redesign_diagnostics.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v5_redesign_diagnostics.py --check
	$(PYTHON) -m unittest simulator.tests.test_v5_diagnostics -v

r2-14a-diagnostic-contract-check:
	$(PYTHON) scripts/check_r2_14a_diagnostic_contract.py
	$(PYTHON) -m unittest simulator.tests.test_v5_diagnostic_contract -v

r2-14-qualification-check:
	$(PYTHON) scripts/run_v4_qualification.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v4_qualification.py --check
	$(PYTHON) -m unittest simulator.tests.test_v4_config simulator.tests.test_v4_corpus simulator.tests.test_v4_qualification -v

r2-13-diagnostic-readiness-check:
	$(PYTHON) scripts/run_v4_redesign_diagnostics.py --readiness-check >/dev/null
	$(PYTHON) scripts/run_v4_redesign_diagnostics.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_v4_diagnostics.py' -v

r2-12-diagnostic-contract-check:
	$(PYTHON) scripts/check_r2_12_diagnostic_contract.py

v3-acceptance-check:
	$(PYTHON) scripts/run_v3_statistical_acceptance.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_v3_acceptance.py' -v

v3-evaluation-check:
	$(PYTHON) scripts/check_v3_evaluation_support.py --check
	$(PYTHON) scripts/build_v3_evaluation_pipeline.py --check

v3-corpus-check:
	$(PYTHON) scripts/build_v3_modeling_corpus.py --check
	$(PYTHON) -m unittest simulator.tests.test_v3_config simulator.tests.test_v3_corpus simulator.tests.test_v3_1_corpus -v

r2-08-design-check:
	$(PYTHON) scripts/check_r2_08_design.py

v2-acceptance-check:
	$(PYTHON) scripts/run_v2_statistical_acceptance.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_v2_acceptance.py' -v

v2-evaluation-check:
	$(PYTHON) scripts/build_v2_evaluation_pipeline.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_v2_evaluation.py' -v

v2-corpus-check:
	$(PYTHON) scripts/build_v2_modeling_corpus.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_v2_*.py' -v

boundary-check:
	./scripts/check_repository_boundaries.sh

dataset-check:
	$(PYTHON) scripts/build_sample_dataset.py --check

assessment-check:
	$(PYTHON) scripts/assess_synthetic_rates.py --check

observation-check:
	$(PYTHON) scripts/build_observations.py --check

temporal-split-check:
	$(PYTHON) scripts/build_temporal_splits.py --check

feature-pipeline-check:
	$(PYTHON) scripts/build_feature_pipeline.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_feature_pipeline.py' -v

logistic-baseline-check:
	$(PYTHON) scripts/train_logistic_baseline.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_logistic_baseline.py' -v

boosted-comparison-check:
	$(PYTHON) scripts/train_boosted_comparison.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_boosted_comparison.py' -v

feature-diagnostics-check:
	$(PYTHON) scripts/run_feature_diagnostics.py --check
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_feature_diagnostics.py' -v

scoring-authorization-check:
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_scoring_authorization.py' -v

leakage-check:
	$(PYTHON) -m unittest discover -s simulator/tests -p 'test_leakage_guards.py' -v

test: contract-test inference-runtime-check simulator-test

contract-test:
	$(PYTHON) -m unittest discover -s data-contracts/tests -v

simulator-test:
	$(PYTHON) -m unittest discover -s simulator/tests -v
