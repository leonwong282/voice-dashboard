PYTHON ?= python3

.PHONY: dev lint test smoke build check clean

dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m pyflakes voice.py voice_dashboard tests

test:
	$(PYTHON) -m pytest -q

smoke:
	ttsrun --help
	ttsrun --version
	ttsrun run --help
	MINIMAX_API_KEY=smoke-test-key ttsrun doctor
	ttsrun config path
	ttsrun config example

build:
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

check: lint test smoke build

clean:
	rm -rf build dist .pytest_cache .ruff_cache *.egg-info
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
