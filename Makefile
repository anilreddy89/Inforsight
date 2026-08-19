.PHONY: check test assessment-check boundary-check contract-test dataset-check leakage-check observation-check simulator-test temporal-split-check

check: boundary-check dataset-check assessment-check observation-check temporal-split-check leakage-check test

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

leakage-check:
	python3 -m unittest discover -s simulator/tests -p 'test_leakage_guards.py' -v

test: contract-test simulator-test

contract-test:
	python3 -m unittest discover -s data-contracts/tests -v

simulator-test:
	python3 -m unittest discover -s simulator/tests -v
