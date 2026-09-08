.PHONY: test lint fixtures example openapi mapping conformance verify
test:
	python -m pytest -q
lint:
	python -m ruff check src tests tools examples
fixtures:
	python tools/validate_fixtures.py
example:
	python examples/worked_example.py
openapi:
	python tools/gen_openapi.py
mapping:
	python tools/gen_mapping_csv.py
conformance:
	python tools/conformance_report.py
verify:
	python tools/verify_public_release.py --files-only
