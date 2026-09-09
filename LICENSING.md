# Licence coverage

This repository is licensed in two components: **Apache License 2.0** for software, CI, build, automation and container configuration; **CC BY 4.0** for documentation, specifications and non-code repository metadata. These licences cover different components, not a choice of either licence for every file. Third-party material retains its own terms.

The Apache-2.0 software grant is the licence this repository has carried since its specification and reference implementation were first published. A change to MIT was introduced in commit `fb16abe` without a recorded decision; it has been reverted, and Apache-2.0 restored.

This map applies to the public files listed in public-release-policy.json. It does not publish or license excluded private reviews, evidence, local files or Git history.

## Apache-2.0 coverage

The software and configuration grant is in [LICENSE](LICENSE).

| Directory or file | Coverage |
| --- | --- |
| src/** | Reference implementation and package source resources |
| tools/** | Generators, release verification and conformance tooling |
| tests/** | Tests, including conformance tests and embedded inputs |
| examples/**/*.py | Executable Python examples |
| setup.py, verify_files.py, Makefile | Build, reference and conformance executables |
| pyproject.toml, pytest.ini | Package/build and test configuration |
| constraints-py311-py312-py313.txt | Pinned dependency constraints for reproducible builds and CI |
| MANIFEST.in, public-release-policy.json | Distribution inclusion and release automation configuration |
| .dockerignore, .editorconfig, .gitattributes, .gitignore | Container, editor and repository tooling configuration |
| .github/workflows/** | CI and automation workflows |
| .github/ISSUE_TEMPLATE/** | Structured issue-form configuration |
| docker/** | Container build and example service configuration |
| LICENSE | Apache-2.0 grant and software copyright notice |

The Apache-2.0 grant covers the software and configuration components only; it does not override the separately scoped CC BY 4.0 documentation/specification grant below. The Markdown pull-request template is non-code contribution documentation, covered in the next table; structured issue forms and executable workflows are Apache-2.0 configuration.

## CC BY 4.0 coverage

The documentation/specification grant and attribution are in [LICENSE-DOCS](LICENSE-DOCS).

| Directory or file | Coverage |
| --- | --- |
| docs/** | Guides, explanatory material and documentation assets |
| spec/schemas/** | JSON schemas |
| spec/ontology/** | Ontology artefacts |
| spec/vocabularies/** | Controlled vocabularies |
| spec/mappings/** | Mapping tables, schemas and mapping documentation |
| spec/queries/** | SPARQL conformance queries and their expected-result fixtures |
| spec/governance/** | Governance record schemas and unpopulated templates |
| spec/openapi/** | Generated OpenAPI exchange specifications |
| spec/access-matrix.json, spec/reason-codes.json | Specification policy and reason-code catalogues |
| examples/**/*.json, examples/**/*.xml, examples/**/*.md | Non-code synthetic fixtures and example documentation |
| README.md, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, PUBLICATION_BOUNDARY.md, LICENSING.md | Repository-root prose and documentation |
| CITATION.cff, MANIFEST.sha256 | Non-code citation and generated integrity metadata |
| .github/PULL_REQUEST_TEMPLATE.md | Non-code contribution documentation |
| LICENSE-DOCS | Documentation/specification grant and attribution notice |

Synthetic example. Not SORT4CIRC project data.

The licence of a generator does not determine the licence of its output. The executable OpenAPI generator is Apache-2.0; the generated OpenAPI specification is CC BY 4.0. Its licence metadata comes from the application definition, never from a stale previously generated file. Likewise, MANIFEST.in is build configuration, while MANIFEST.sha256 is generated non-code metadata.

## Distributions and generated files

The Python distribution includes Apache-2.0 software and CC BY 4.0 specifications. Package metadata uses Apache-2.0 AND CC-BY-4.0 to describe this combined distribution; the per-file map above controls component scope. Bundled sort4circ_dpp/spec/** resources retain the CC BY 4.0 grant of their source spec/** files.

Both grants and this coverage notice accompany source and wheel distributions. CITATION.cff lists the licences of the cited components; the citation file itself is CC BY 4.0 metadata. Generated manifests record inclusion/integrity and do not change the licences of the files they list. Regeneration must preserve the component split.

## Coverage status

Every file in `public-release-policy.json` matches exactly one scope in the tables above, and `tests/test_licensing.py` asserts that. New public files must be assigned an explicit component scope when added to the release policy.

The generated OpenAPI document is a specification asset and carries the CC BY 4.0 grant, consistent with the rest of `spec/`. This resolves the earlier conflict between the OpenAPI's own licence metadata and the declared specification licence.

Coverage being unambiguous is a statement about this map, not an approval record. Private security reporting arrangements, Git history and public-release sign-off remain separate matters.

## Third-party review

The explicit public source file set was reviewed for vendored code, copied implementation notices, bundled dependencies and attributed external material. No vendored third-party implementation or copied standards document requiring a separate THIRD_PARTY_NOTICES.md was identified, so no such file is created.

External dependencies are identified in pyproject.toml: FastAPI, Uvicorn, jsonschema and Pydantic; optional development tools include pytest, HTTPX, Ruff, RDFLib, PyYAML and xmlschema. Setuptools and wheel supply build tooling. CI references GitHub Actions, and the optional container uses a Python base image. These components are not relicensed as Apache-2.0 or CC BY 4.0 by this repository; installed or redistributed copies retain their own licence and notice files.

References to JSON Schema, W3C vocabularies, GS1 encodings and regulatory fibre terminology identify external concepts. This repository's grants do not license the referenced standards or external publications. The coverage of the repository's licence notices does not relicense external legal texts. No dependency notices, installed third-party licence files or external licence terms were changed. This source inspection does not establish ownership of material whose provenance has not been documented.
