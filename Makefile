.PHONY: check test boundary-check

check: boundary-check test

boundary-check:
	./scripts/check_repository_boundaries.sh

test:
	python3 -m unittest discover -s simulator/tests -v
