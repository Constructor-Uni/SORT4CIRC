# Execution evidence

New evidence-producing runs write `evidence/runs/<run-id>/evidence.json` and
`raw-result.json`. Pass that run directory with `--evidence-dir` to
`tools/loadtest.py` or `tools/anchor_bench.py`; the conformance tool accepts
it as its optional positional argument. Run directories are intentionally
ignored by Git and the delivery manifest so creating evidence does not make an
otherwise clean source tree dirty.

`evidence.json` follows
`evidence/schema/execution-evidence-1.0.0.schema.json`. It records the full
commit, dirty state, application and dependency versions, runtime and hardware
facts, pinned container references, configuration profile, dataset identity,
counts and characteristics, normative artefact versions and digests,
acceptance target/rule/observation/verdict, and the raw result digest and size.
The working directory is recorded logically as `repositoryRoot`, not as a
personal absolute path.

SHA-256 over structured configuration uses canonical UTF-8 JSON with sorted
keys and compact separators (`json-sorted-keys-utf8-1.0.0`). Dataset file-set
digests hash each sorted repository-relative name, a NUL byte, exact content,
and a final NUL byte. Generated datasets hash their canonical input payloads.
Raw results and individual normative artefacts are hashed as exact bytes.
Vocabulary releases use the file-set algorithm. Volatile filesystem metadata
is never hashed.

Configuration keys that may contain credentials, tokens, endpoints, private
addresses or adapter options are omitted before both recording and hashing.
Evidence therefore describes only non-secret parameters that affect the run.

An `executedTest` is produced by a command run and has a raw result.
`inspection` describes a direct examination without exercising the system.
`documentary` records supporting documentary material; neither label may be
used to imply an executed test. The bundled tools currently emit
`executedTest`.

Ordinary runs are classified as research evidence. A dirty run is always
`releaseGrade: false`. Passing `--release-evidence` requires a clean working
tree and is rejected otherwise. Existing benchmark files are historical facts
and are not rewritten. In particular,
`docs/benchmarks/loadtest-results.json` records commit `d870cc9`, which is
not reachable from the current repository history; the new framework does not
substitute a different commit.

Examples:

```text
python tools/loadtest.py --passports 10 --requests 20 --concurrency 1 --evidence-dir evidence/runs/load-local
python tools/anchor_bench.py --self-test --runs 10 --evidence-dir evidence/runs/anchor-self-test
python tools/conformance_report.py evidence/runs/conformance-local
python tools/evidence_run.py tests --evidence-dir evidence/runs/tests-local
python tools/evidence_run.py fixtures --evidence-dir evidence/runs/fixtures-local
python tools/evidence_run.py mapping --evidence-dir evidence/runs/mapping-local
```

Validate a record with:

```text
python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; s=json.loads(Path('evidence/schema/execution-evidence-1.0.0.schema.json').read_text()); V(s).validate(json.loads(Path('evidence/runs/load-local/evidence.json').read_text()))"
```
