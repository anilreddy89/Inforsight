.PHONY: check test boundary-check contract-test simulator-test

check: boundary-check test

boundary-check:
	./scripts/check_repository_boundaries.sh

test: contract-test simulator-test

contract-test:
	python3 -m unittest discover -s data-contracts/tests -v

simulator-test:
	python3 -m unittest discover -s simulator/tests -v
