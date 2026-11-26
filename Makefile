# Course maintenance tasks. Students need only the commands in the README; instructors use these.

.PHONY: help install install-locked test notebooks pages diagrams schedule check verify lint data app clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install course + notebook requirements (latest compatible)
	pip install -r requirements.txt -r requirements-dev.txt

install-locked:  ## Install the exact versions the course was tested with
	pip install -r requirements-lock.txt -r requirements-dev.txt

data:  ## Download the SKAB project data (~4 MB) and verify it
	python project/get_skab.py
	python project/get_skab.py --verify

test:  ## Course tests: helpers, tools, site markup (fast, no data needed)
	python -m pytest tests -q

notebooks:  ## Rebuild notebooks/*.ipynb from notebook_src/*.py
	python tools/nbbuild.py

pages:  ## Render notebooks into docs/notebooks/ for the course site
	python tools/nbpages.py

diagrams:  ## Render docs/assets/diagrams/src/*.mmd to SVG (needs Node + Playwright)
	python tools/make_diagrams.py

schedule:  ## Regenerate advanced/course.json and docs/advanced/schedule.md
	python tools/build_course.py

check:  ## Everything CI checks except the long lab verification
	python tools/build_course.py && git diff --exit-code advanced/course.json docs/advanced/schedule.md
	python tools/nbbuild.py --check
	python tools/nbpages.py --check
	python tools/make_diagrams.py --check
	python tools/check_notebooks.py
	python tools/check_links.py
	python -m pytest tests -q

verify:  ## Every reference solution passes and every wrong submission is rejected (~30 min)
	python tools/verify_checks.py --all

lint:  ## Lint the helpers and tools
	ruff check src tools scripts tests

app:  ## Start the local study app
	streamlit run app/study_app.py

clean:  ## Remove caches and generated run outputs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
