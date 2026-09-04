.PHONY: check test assessment-check boosted-comparison-check boundary-check contract-test dataset-check feature-diagnostics-check feature-pipeline-check leakage-check logistic-baseline-check observation-check r2-08-design-check r2-12-diagnostic-contract-check r2-13-diagnostic-readiness-check r2-14-qualification-check r2-14a-diagnostic-contract-check r2-14b-diagnostic-check r2-14ba-diagnostic-contract-check r2-14bb-diagnostic-check scoring-authorization-check simulator-test temporal-split-check v2-acceptance-check v2-corpus-check v2-evaluation-check v3-acceptance-check v3-corpus-check v3-evaluation-check serve-roadmap check-contracts check-v1-v3 check-v4-v5

serve-roadmap:
	python3 scripts/serve_roadmap.py

check: check-contracts check-v1-v3 check-v4-v5 simulator-test

check-contracts: boundary-check dataset-check contract-test r2-08-design-check r2-12-diagnostic-contract-check r2-14a-diagnostic-contract-check r2-14ba-diagnostic-contract-check

check-v1-v3: assessment-check observation-check temporal-split-check feature-pipeline-check logistic-baseline-check boosted-comparison-check feature-diagnostics-check scoring-authorization-check leakage-check v2-corpus-check v2-evaluation-check v2-acceptance-check v3-corpus-check v3-evaluation-check v3-acceptance-check

check-v4-v5: r2-13-diagnostic-readiness-check r2-14-qualification-check r2-14b-diagnostic-check r2-14bb-diagnostic-check

r2-14bb-diagnostic-check:
	python3 scripts/run_v5_redesign_diagnostics_execution.py --readiness-check >/dev/null
	python3 scripts/run_v5_redesign_diagnostics_execution.py --check
	python3 -m unittest simulator.tests.test_v5_diagnostics_execution -v

r2-14ba-diagnostic-contract-check:
	python3 scripts/check_r2_14ba_diagnostic_contract.py
	python3 -m unittest simulator.tests.test_v5_diagnostic_contract_amendment -v

r2-14b-diagnostic-check:
	! python3 scripts/run_v5_redesign_diagnostics.py --readiness-check >/dev/null
	python3 scripts/run_v5_redesign_diagnostics.py --check
	python3 -m unittest simulator.tests.test_v5_diagnostics -v

r2-14a-diagnostic-contract-check:
	python3 scripts/check_r2_14a_diagnostic_contract.py
	python3 -m unittest simulator.tests.test_v5_diagnostic_contract -v

r2-14-qualification-check:
	python3 scripts/run_v4_qualification.py --readiness-check >/dev/null
	python3 scripts/run_v4_qualification.py --check
	python3 -m unittest simulator.tests.test_v4_config simulator.tests.test_v4_corpus simulator.tests.test_v4_qualification -v

r2-13-diagnostic-readiness-check:
	python3 scripts/run_v4_redesign_diagnostics.py --readiness-check >/dev/null
	python3 scripts/run_v4_redesign_diagnostics.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_v4_diagnostics.py' -v

r2-12-diagnostic-contract-check:
	python3 scripts/check_r2_12_diagnostic_contract.py

v3-acceptance-check:
	python3 scripts/run_v3_statistical_acceptance.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_v3_acceptance.py' -v

v3-evaluation-check:
	python3 scripts/check_v3_evaluation_support.py --check
	python3 scripts/build_v3_evaluation_pipeline.py --check

v3-corpus-check:
	python3 scripts/build_v3_modeling_corpus.py --check
	python3 -m unittest simulator.tests.test_v3_config simulator.tests.test_v3_corpus simulator.tests.test_v3_1_corpus -v

r2-08-design-check:
	python3 scripts/check_r2_08_design.py

v2-acceptance-check:
	python3 scripts/run_v2_statistical_acceptance.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_v2_acceptance.py' -v

v2-evaluation-check:
	python3 scripts/build_v2_evaluation_pipeline.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_v2_evaluation.py' -v

v2-corpus-check:
	python3 scripts/build_v2_modeling_corpus.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_v2_*.py' -v

boundary-check:
	./scripts/check_repository_boundaries.sh

dataset-check:
	python3 scripts/build_sample_dataset.py --check

assessment-check:
	python3 scripts/assess_synthetic_rates.py --check

observation-check:
	python3 scripts/build_observations.py --check

temporal-split-check:
	python3 scripts/build_temporal_splits.py --check

feature-pipeline-check:
	python3 scripts/build_feature_pipeline.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_feature_pipeline.py' -v

logistic-baseline-check:
	python3 scripts/train_logistic_baseline.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_logistic_baseline.py' -v

boosted-comparison-check:
	python3 scripts/train_boosted_comparison.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_boosted_comparison.py' -v

feature-diagnostics-check:
	python3 scripts/run_feature_diagnostics.py --check
	python3 -m unittest discover -s simulator/tests -p 'test_feature_diagnostics.py' -v

scoring-authorization-check:
	python3 -m unittest discover -s simulator/tests -p 'test_scoring_authorization.py' -v

leakage-check:
	python3 -m unittest discover -s simulator/tests -p 'test_leakage_guards.py' -v

test: contract-test simulator-test

contract-test:
	python3 -m unittest discover -s data-contracts/tests -v

simulator-test:
	python3 -m unittest discover -s simulator/tests -v
