.DEFAULT_GOAL := help

.PHONY: help
# Adapted from:
# https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## List Makefile targets
	$(info Makefile documentation)
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev:  ## Create local development environment
	@poetry install --sync
	@poetry run pre-commit install

.PHONY: lint
lint: dev  ## Run local linters
	@poetry run pre-commit run --all-files
	@poetry run zizmor . --no-online-audits --min-severity=medium
	@poetry run yamllint .github/workflows/
