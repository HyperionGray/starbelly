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
	poetry install --no-interaction
	poetry run pytest -q
