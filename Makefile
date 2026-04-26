.PHONY: help clean lint test coverage build

help:
	@echo "clean    - remove build, test, and coverage artifacts"
	@echo "lint     - check style (black, isort)"
	@echo "test     - run tests with tox (py314)"
	@echo "coverage - run tests with coverage report"
	@echo "build    - build source and wheel distributions"

clean:
	rm -rf build/ dist/ .eggs/ htmlcov/ .coverage coverage.xml
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.pyc' -o -name '*.pyo' | xargs rm -f
	find . -name '__pycache__' -exec rm -rf {} +

lint:
	tox -e lint

test:
	tox -e py314

coverage:
	tox -e coverage

build: clean
	python -m build
