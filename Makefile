# The targets in this makefile should be executed inside Poetry, i.e. `poetry run make
# docs`.

.PHONY: docs test ci-check repo-hygiene

docs:
	$(MAKE) -C docs html

test:
	pytest tests/ --cov=starbelly --cov-report=term-missing

repo-hygiene:
	python3 tools/repo_hygiene.py

ci-check:
	python3 tools/repo_hygiene.py --tracked-only
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Poetry is required for ci-check. Install it with: python3 -m pip install poetry"; \
		exit 1; \
	fi
	poetry install --no-interaction
	poetry run pytest -q
