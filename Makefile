.PHONY: check test assessment-check boosted-comparison-check boundary-check contract-test dataset-check feature-diagnostics-check feature-pipeline-check leakage-check logistic-baseline-check observation-check scoring-authorization-check simulator-test temporal-split-check v2-corpus-check

check: boundary-check dataset-check assessment-check observation-check temporal-split-check feature-pipeline-check logistic-baseline-check boosted-comparison-check feature-diagnostics-check scoring-authorization-check leakage-check v2-corpus-check test

v2-corpus-check:
	.venv/bin/python scripts/build_v2_modeling_corpus.py --check
	.venv/bin/python -m unittest discover -s simulator/tests -p 'test_v2_*.py' -v

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
