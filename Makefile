# HealthGuard AI — dataset, verification and tests.
#
# The dataset pipeline is pure standard library, so `verify`, `verify-full`
# and the dataset tests run without installing anything. Only `train` needs
# the pinned requirements.

ML := kinyamed/ml_model
PY := python3

.DEFAULT_GOAL := help
.PHONY: help install install-dev test verify verify-full sample dataset splits freeze clean

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*?## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install training dependencies (pinned)
	$(PY) -m pip install -r $(ML)/requirements.txt

install-dev:  ## Install test dependencies
	$(PY) -m pip install -r $(ML)/requirements-dev.txt

test:  ## Run the test suite
	cd $(ML) && $(PY) -m pytest -q

verify:  ## Re-derive the committed sample and its splits from seed 42 (seconds)
	cd $(ML) && $(PY) verify.py --scope sample

verify-full:  ## Regenerate all 1M rows and check every frozen digest (~1 min, ~1GB scratch)
	cd $(ML) && $(PY) verify.py --scope full

sample:  ## Regenerate the committed 1,000-row sample
	cd $(ML) && $(PY) dataset/generate_large_dataset.py \
		--target 1000 --seed 42 --output dataset/sample/symptoms_sample.csv

dataset:  ## Generate the full 1M-row corpus and validate it (not committed)
	cd $(ML) && $(PY) dataset/generate_large_dataset.py --target 1000000 --seed 42
	cd $(ML) && $(PY) dataset/validate_dataset.py \
		--report dataset/raw/symptoms_large.validation.json

splits:  ## Build both leakage-controlled splits from the corpus
	cd $(ML) && $(PY) dataset/split_dataset.py --strategy phrase
	cd $(ML) && $(PY) dataset/split_dataset.py --strategy family

freeze:  ## Freeze both eval sets to versioned manifests with digests
	cd $(ML) && $(PY) dataset/freeze_eval.py --strategy phrase
	cd $(ML) && $(PY) dataset/freeze_eval.py --strategy family

clean:  ## Remove generated data, split state and crash debris
	rm -f  $(ML)/dataset/raw/symptoms_large.csv
	rm -f  $(ML)/dataset/processed/*_holdout.csv
	rm -rf $(ML)/dataset/processed/.split_*_state
	find $(ML) -name '*.partial' -delete
	find $(ML) -name '__pycache__' -type d -prune -exec rm -rf {} +
