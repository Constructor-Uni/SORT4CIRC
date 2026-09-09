# Contributing

Contributions of generic DPP concepts, corrections, documentation improvements and
independently synthetic examples are welcome.

## Rule 1 — nothing real, ever

**Contributions must not include:**

- real consortium partner datasets;
- confidential project information;
- personal data;
- credentials, API keys, passwords, access tokens;
- private keys, seed phrases or wallet credentials;
- private endpoints, internal hostnames or IP addresses;
- raw pilot logs or operational industrial data;
- deployment configuration, private blockchain deployment information, or other
  security-sensitive material.

This applies to **everything** in a contribution or a report: payloads, code, tests,
fixtures, attachments, screenshots, logs, commit messages and follow-up comments. It applies
to private security reports as well as public pull requests.

All examples and fixtures must be **synthetic and demonstrative**. Generate them with
`SyntheticFixtureFactory` and use the reserved `urn:example:` and `https://example.org/`
namespaces. Do not relabel a real record as synthetic; construct a new one.

If you need to report something you believe was exposed, describe the concern without
reproducing the exposed content, and use the private channel in [SECURITY.md](SECURITY.md).

## Choosing the reporting channel

| Kind | Where |
| --- | --- |
| Bug, feature request, specification question, documentation improvement | A public GitHub issue |
| Security vulnerability, or suspected accidental exposure of confidential data | **GitHub Private Vulnerability Reporting** — never a public issue, pull request, discussion or comment |

If private reporting is unavailable, keep the report private rather than opening a public
one. See [SECURITY.md](SECURITY.md).

## Setting up

~~~sh
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
python -m venv .venv
# sh/bash:    source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

Python 3.11 or later. See [Getting started](docs/getting-started.md).

## Running the checks

Run all of these before opening a pull request. Every one is also a `make` target.

~~~sh
python -m pytest -q                              # full test suite          (make test)
python -m ruff check src tests tools examples    # lint                     (make lint)
python tools/validate_fixtures.py                # every fixture, pos + neg (make fixtures)
python tools/gen_mapping_csv.py --check          # mapping CSV drift        (make mapping)
python tools/gen_openapi.py --check              # OpenAPI drift            (make openapi)
python examples/worked_example.py                # end-to-end example       (make example)
python tools/conformance_report.py               # category summary         (make conformance)
python verify_files.py                           # manifest matches policy
python tools/verify_public_release.py --files-only  # public file policy    (make verify)
~~~

Formatting follows `.editorconfig` and `ruff` (`line-length = 120`, rule sets `E`, `F`,
`W`, `I`, `UP`, `B`, `C4`, `SIM`). Do not reformat unrelated files.

## Adding a fixture

1. Generate it from `SyntheticFixtureFactory` in
   [`src/sort4circ_dpp/synthetic.py`](src/sort4circ_dpp/synthetic.py) — add a variant to
   `fixtures()` rather than hand-writing JSON, so the corpus stays reproducible.
2. A **negative** fixture must carry a test-only `$expect` member naming the reason code it
   must produce. A negative fixture that fails to fail is a silent gap in the schema.
3. Run `python tools/validate_fixtures.py` and confirm the new file behaves as declared.
4. Add the file to `public-release-policy.json` (see below).
5. Note it in [`examples/README.md`](examples/README.md) if it demonstrates something a
   reader should know about.

## Changing a specification asset

The assets in `spec/` are versioned **together**. A change to one usually requires changes
to the others, or the representations silently diverge.

1. **Schema** — `spec/schemas/dpp-1.0.0.schema.json`
2. **Vocabularies** — `spec/vocabularies/*.json`. Add terms; do not redefine existing ones.
   Retire with `deprecated` + `replacedBy`, never by deletion. Bind any new coded field in
   `FIELD_VOCABULARIES` in [`src/sort4circ_dpp/vocab.py`](src/sort4circ_dpp/vocab.py).
3. **XSD** — `spec/schemas/dpp-1.0.0.xsd`
4. **Ontology** — `spec/ontology/sort4circ-1.0.1.ttl`
5. **Mapping** — one row per schema-defined exchange path in
   `spec/mappings/dpp-mapping-1.0.0.json`, then regenerate the CSV with
   `python tools/gen_mapping_csv.py`
6. **Access matrix** — if a new field needs a view decision, make it explicitly in
   `spec/access-matrix.json`
7. **Reason codes** — a new failure condition needs an entry in `spec/reason-codes.json`
8. **Fixtures and tests** — new behaviour needs both a positive and a negative case
9. **OpenAPI** — regenerate with `python tools/gen_openapi.py`; it is generated from the
   application and must never be hand-edited

Then run the full check list above. `tests/test_mapping.py` is the guard that catches
assets drifting apart, and `python tools/gen_mapping_csv.py --check` and
`python tools/gen_openapi.py --check` catch generated files that were not regenerated.

## Adding a public file

The repository publishes an **explicit allowlist**, not "whatever is in the tree". A new
public file needs three things:

1. an entry in `public-release-policy.json`;
2. licence coverage in [`LICENSING.md`](LICENSING.md) — every public file must match
   **exactly one** component scope (`tests/test_licensing.py` enforces this);
3. regenerated manifests:

~~~sh
python verify_files.py --write     # updates MANIFEST.in and MANIFEST.sha256
python verify_files.py             # verifies
~~~

A manifest update must never silently expand the allowed content. Review policy additions
deliberately; the allowlist is the mechanism that keeps unreviewed material out of a
release.

Markdown links in published files must resolve to existing local files —
`tests/test_public_release.py` checks this, so a link to a directory or a moved page fails
the build.

## Writing documentation

- Documentation lives in `docs/` and is organised around **developer questions**, not
  deliverable section numbers. Add to an existing page before creating a new one.
- A new page must be linked from [`docs/index.md`](docs/index.md), and usually from the
  "I want to…" table in [`README.md`](README.md).
- Do not claim legal conformity, certification, external standard conformity or production
  assurance from the checks in this repository. Say what was tested.
- Keep "normative" scoped: normative **within this profile**. See
  [docs/regulatory-context.md](docs/regulatory-context.md).

## Pull requests

State:

- which profile rule or behaviour is affected;
- the behaviour before and after;
- which checks you ran, and their results;
- whether any specification asset version needs to change.

New schema, vocabulary or API behaviour needs tests. Do not weaken an existing test to make
a change pass — if a test fails because the documentation, specification or code is
genuinely inconsistent, fix the inconsistency.

## Licensing of contributions

The repository uses a two-component split, recorded per path in
[`LICENSING.md`](LICENSING.md):

- **Apache-2.0** for software, tests, tools, and build/CI/container configuration;
- **CC BY 4.0** for documentation, specifications, schemas, vocabularies, ontology,
  mappings, OpenAPI, JSON fixtures and repository prose and metadata.

Contribute only material you have the right to contribute under the applicable component
licence. Retain third-party notices, and do not add copies of external standards documents.
