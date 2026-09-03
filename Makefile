# HealthGuard AI — dataset, verification and tests.
#
# The dataset pipeline is pure standard library, so `verify`, `verify-full`
# and the dataset tests run without installing anything. Only `train` needs
# the pinned requirements.

ML := kinyamed/ml_model
PY := python3

.DEFAULT_GOAL := help
.PHONY: help install install-dev test test-clean check-attribution install-hooks verify verify-full sample dataset splits freeze clean

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*?## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install training dependencies (pinned)
	$(PY) -m pip install -r $(ML)/requirements.txt

install-dev:  ## Install test dependencies
	$(PY) -m pip install -r $(ML)/requirements-dev.txt

test:  ## Run the test suite
	@$(PY) -c "import pytest" 2>/dev/null || { \
		echo "pytest is not installed. Run 'make install-dev' first."; \
		echo "(note: 'make verify' needs no dependencies at all)"; exit 1; }
	cd $(ML) && $(PY) -m pytest -q

test-clean:  ## Run the suite in a throwaway clone of HEAD — catches ambient-state bugs
	@set -e; \
	if ! git diff --quiet HEAD -- $(ML) 2>/dev/null; then \
		echo "NOTE: uncommitted changes under $(ML) are NOT included."; \
		echo "      This tests HEAD ($$(git rev-parse --short HEAD)) — i.e. what a push would publish."; \
		echo ""; \
	fi; \
	tmp=$$(mktemp -d -t healthguard-testclean-XXXXXX); \
	trap 'rm -rf "$$tmp"' EXIT INT TERM; \
	git clone --quiet --no-hardlinks . "$$tmp/clone"; \
	echo "clean clone of $$(git -C "$$tmp/clone" rev-parse --short HEAD)"; \
	leaked=$$(find "$$tmp/clone/$(ML)/dataset/raw" "$$tmp/clone/$(ML)/dataset/processed" \
	          -name '*.csv' 2>/dev/null | wc -l); \
	model=$$(find "$$tmp/clone/$(ML)" -name '*.safetensors' 2>/dev/null | wc -l); \
	echo "  generated CSVs present : $$leaked (must be 0)"; \
	echo "  model weights present  : $$model (must be 0)"; \
	if [ "$$leaked" -ne 0 ] || [ "$$model" -ne 0 ]; then \
		echo ""; \
		echo "FAIL: derived data is tracked. A test could pass on ambient state"; \
		echo "      that a fresh clone will not have."; \
		exit 1; \
	fi; \
	py=$$($(PY) -c 'import sys; print(sys.executable)'); \
	if ! "$$py" -c "import pytest" 2>/dev/null; then \
		echo "pytest is not installed. Run 'make install-dev' first."; exit 1; fi; \
	echo "  interpreter            : $$py"; \
	echo ""; \
	cd "$$tmp/clone/$(ML)" && "$$py" -m pytest -q -rs

check-attribution:  ## Attribution sweep over the real authored corpus (~3 min)
	@# Runs inside `test`/`test-clean` too. Called out separately so the guard
	@# survives someone deselecting or marking it slow: attribution has failed
	@# silently three times, and a green suite hid every one of them.
	cd $(ML) && $(PY) -m pytest tests/test_attribution_corpus.py -q

install-hooks:  ## Make pre-push run test-clean automatically
	git config core.hooksPath .githooks
	@echo "pre-push now runs 'make test-clean'."
	@echo "Undo with: git config --unset core.hooksPath"

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
