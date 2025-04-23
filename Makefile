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
	@# This command uses `find` to identify all files *not* in '.venv/' and '.git/', pipes the
	@# output to `awk` to determine if they are shell scripts, and then pipes that filtered
	@# output into shellcheck. See the below resources for rationale and reference
	@# implementations:
	@#
	@# https://stackoverflow.com/a/16595367
	@# https://www.shellcheck.net/wiki/Recursiveness
	@find . -not \( -path ./.git -prune \) -not \( -path ./.venv -prune \) -type f -exec file {} + | awk -F: '/shell script/{print $$1}' | xargs -r shellcheck
