# Makefile: package docs into zip
DOCS_DIR=docs
ZIP_NAME=abacus-docs-1.0.zip

docs-zip:
	@echo "Packaging $(DOCS_DIR) into $(ZIP_NAME)..."
	@rm -f $(ZIP_NAME)
	@zip -r $(ZIP_NAME) $(DOCS_DIR)
	@echo "Created $(ZIP_NAME)"

.PHONY: docs-zip
