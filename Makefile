PYTHON ?= python3

.PHONY: test check-config pilot-summary

test:
	$(PYTHON) -B -m unittest discover -s tests/unit -v

check-config:
	$(PYTHON) -B pipeline/screening/run.py --check-config

pilot-summary:
	$(PYTHON) -B pipeline/screening/summarize_pilot.py
