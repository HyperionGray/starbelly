# The targets in this makefile should be executed inside Poetry, i.e. `poetry run make
# docs`.

.PHONY: docs

docs:
	$(MAKE) -C docs html

test:
	pytest tests/ --cov=starbelly --cov-report=term-missing
