PYTHON ?= python3

.PHONY: dev lint test build check clean

dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m pyflakes voice.py voice_dashboard tests

test:
	$(PYTHON) -m pytest -q

build:
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

check: lint test build

clean:
	rm -rf build dist .pytest_cache .ruff_cache *.egg-info
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
