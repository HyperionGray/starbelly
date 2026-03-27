# The targets in this makefile should be executed inside Poetry, i.e. `poetry run make
# docs`.

.PHONY: docs test repo-hygiene

docs:
	$(MAKE) -C docs html

test:
	pytest tests/ --cov=starbelly --cov-report=term-missing

repo-hygiene:
	python tools/repo_hygiene.py
