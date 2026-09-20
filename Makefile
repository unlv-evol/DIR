PYTHON ?= python3

.PHONY: test check-config

test:
	$(PYTHON) -B -m unittest discover -s tests/unit -v

check-config:
	$(PYTHON) -B pipeline/screening/run.py --check-config
