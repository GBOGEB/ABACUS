# Makefile: package docs into zip and provide dev convenience targets
DOCS_DIR=docs
ZIP_NAME=abacus-docs-1.0.zip
PYTHON=python
PYTEST=$(PYTHON) -m pytest
FLAKE8=$(PYTHON) -m flake8

docs-zip:
	@echo "Packaging $(DOCS_DIR) into $(ZIP_NAME)..."
	@rm -f $(ZIP_NAME)
	@zip -r $(ZIP_NAME) $(DOCS_DIR)
	@echo "Created $(ZIP_NAME)"

test:
	$(PYTEST) DMAIC_V3/tests -q

lint:
	$(FLAKE8) DMAIC_V3/core/test_system_bridge.py run_deployment_test_system.py --max-line-length=120

smoke:
	$(PYTEST) DMAIC_V3/tests -q -m smoke

patch-bundle:
	@echo "Building session patch bundle..."
	@$(PYTHON) scripts/generate_docs_html.py
	@echo "Patch bundle ready in $(DOCS_DIR)/"

.PHONY: docs-zip test lint smoke patch-bundle
