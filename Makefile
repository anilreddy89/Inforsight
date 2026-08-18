.PHONY: check test boundary-check contract-test dataset-check simulator-test

check: boundary-check dataset-check test

boundary-check:
	./scripts/check_repository_boundaries.sh

dataset-check:
	python3 scripts/build_sample_dataset.py --check

test: contract-test simulator-test

contract-test:
	python3 -m unittest discover -s data-contracts/tests -v

simulator-test:
	python3 -m unittest discover -s simulator/tests -v
