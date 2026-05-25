.PHONY: help clean lint test coverage build install

help:
	@echo "clean    - remove build, test, and coverage artifacts"
	@echo "lint     - check style with ruff"
	@echo "test     - run tests with pytest"
	@echo "coverage - run tests with coverage report"
	@echo "build    - build source and wheel distributions"
	@echo "install  - install arwn as a systemd user service"

clean:
	rm -rf build/ dist/ .eggs/ htmlcov/ .coverage coverage.xml
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.pyc' -o -name '*.pyo' | xargs rm -f
	find . -name '__pycache__' -exec rm -rf {} +

lint:
	uv run ruff check
	uv run ruff format --check

test:
	uv run pytest

coverage:
	uv run pytest --cov --cov-report=html --cov-report=term

build: clean
	uv build

install:
	uv pip install .
	uv run arwn-install-service
