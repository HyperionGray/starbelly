# The targets in this makefile should be executed inside Poetry, i.e. `poetry run make
# docs`.

.PHONY: docs test setup-env check-env

docs:
	$(MAKE) -C docs html

test:
	pytest tests/ --cov=starbelly --cov-report=term-missing

setup-env:
	./bin/setup-env.sh

check-env:
	./bin/check-env.sh
