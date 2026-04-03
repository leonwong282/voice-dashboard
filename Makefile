PYTHON ?= python3

.PHONY: dev lint test smoke build dist-sha256 homebrew-formula release-smoke check clean

dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m pyflakes voice.py voice_dashboard tests scripts

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
	rm -rf build dist
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

dist-sha256: build
	shasum -a 256 dist/*.tar.gz

homebrew-formula:
	$(PYTHON) scripts/render_homebrew_formula.py --source-url "$(SOURCE_URL)" --source-sha256 "$(SOURCE_SHA256)"

release-smoke: build
	tmpdir=$$(mktemp -d); \
	"$(PYTHON)" -m venv "$$tmpdir/venv"; \
	"$$tmpdir/venv/bin/python" -m pip install --upgrade pip >/dev/null; \
	"$$tmpdir/venv/bin/python" -m pip install dist/*.whl >/dev/null; \
	"$$tmpdir/venv/bin/ttsrun" --help >/dev/null; \
	"$$tmpdir/venv/bin/ttsrun" --version; \
	MINIMAX_API_KEY=smoke-test-key "$$tmpdir/venv/bin/ttsrun" doctor >/dev/null; \
	"$$tmpdir/venv/bin/ttsrun" config path >/dev/null; \
	"$$tmpdir/venv/bin/ttsrun" config example >/dev/null; \
	rm -rf "$$tmpdir"

check: lint test smoke build

clean:
	rm -rf build dist .pytest_cache .ruff_cache *.egg-info
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
