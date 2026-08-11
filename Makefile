.PHONY: help install test conformance example serve openapi lint clean docker

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install:  ## Install the package with development extras
	python3 -m pip install -e ".[dev]"

test:  ## Run the full test suite
	python3 -m pytest -q

conformance:  ## Run the conformance suite and write conformance-report.json
	python3 tools/conformance_report.py

example:  ## Run the D4.3 Annex G worked example end to end
	python3 examples/worked_example.py

serve:  ## Start the reference API on port 8000
	S4C_ALLOW_HEADER_AUTH=1 python3 -m uvicorn sort4circ_dpp.api:app --app-dir src --reload --port 8000

openapi:  ## Regenerate spec/openapi/dpp-api-v1.json from the running contract
	python3 tools/gen_openapi.py

validate:  ## Validate every fixture against the schema and vocabularies
	python3 tools/validate_fixtures.py

lint:  ## Static checks
	python3 -m ruff check src tests tools examples

docker:  ## Build the container image
	docker build -f docker/Dockerfile -t sort4circ/dpp:1.0.0 .

clean:
	rm -rf .pytest_cache **/__pycache__ conformance-report.json
