.PHONY: docs

docs:
	cd docs && pipenv run make html

init:
	pip install codecov pipenv
	pipenv install --dev

test:
	pipenv run pytest --cov=starbelly tests
	codecov
