.PHONY: install aggregate report paper lint format test check

install:
	uv sync

aggregate:
	uv run python scripts/run.py aggregate

report:
	uv run python scripts/run.py report

paper: report
	cd ms && latexmk -xelatex -interaction=nonstopmode -halt-on-error report.tex

lint:
	uv run black --check pakdk scripts tests
	uv run isort --check-only pakdk scripts tests
	uv run flake8 pakdk scripts tests

format:
	uv run isort pakdk scripts tests
	uv run black pakdk scripts tests

test:
	uv run pytest -q

check: lint test
	$(MAKE) report
	git diff --exit-code tabs
	$(MAKE) paper
	@! grep -E "undefined|Citation .* undefined" ms/report.log
