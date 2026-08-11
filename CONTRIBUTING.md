# Contributing

## What kind of change this is

The repository has two halves and they have different rules.

**A change under `spec/` changes what conformance means.** It requires a version
bump on the affected artefact, a migration note in `CHANGELOG.md`, and a test
that fails before the change and passes after it. Open an issue using the
specification template before writing the change, because the discussion is
usually more valuable than the patch.

**A change under `src/` changes the reference implementation.** If it makes the
implementation disagree with `spec/`, it is a bug fix in the implementation, not
a specification change. If the specification turns out to be wrong, say so
explicitly and change `spec/` in a separate commit so the record shows which of
the two moved.

## Rules that are not negotiable

These are invariants, not preferences. A pull request that breaks one will be
refused regardless of what else it improves.

1. **A released vocabulary token is never removed.** Deprecate it and name its
   replacement. Removal invalidates records other parties have already written.
2. **A released reason code is never reworded or renumbered.** Clients dispatch
   on the code. Add a new code instead.
3. **Observations, events, decisions and integrity entries are append only.**
   No change may introduce a path that overwrites one.
4. **No passport content in a ledger envelope.** The envelope carries a
   reference and a digest. This is the property that makes a public ledger
   acceptable at all.
5. **An unknown value is never written as zero, empty or a default category.**
6. **The digest never depends on who asked.** Access decisions and view
   artefacts stay outside the integrity projection.

## Before opening a pull request

```bash
make lint
make test
make validate
make example
```

A change touching the API must regenerate the contract with `make openapi` and
commit the result, so the published contract stays a description of the service
rather than a claim about it.

## Adding a test

Tests carry the checklist row they evidence:

```python
@pytest.mark.checklist("DAT-02", "tier1")
def test_unknown_is_never_coerced_to_zero(client):
    ...
```

If a row genuinely cannot be decided by an automated test, add it to
`REQUIRES_HUMAN_EVIDENCE` in `tests/conformance/test_checklist.py` together with
the evidence that would decide it. Do not delete the row: a suite that quietly
omits half the checklist reads as full coverage when it is not.

## Commit messages

State what changed and why the previous behaviour was wrong. "Fix bug" says
nothing that the diff does not already say.
