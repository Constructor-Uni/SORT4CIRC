## What changed

<!-- State the behaviour before and after. -->

## Which half of the repository

- [ ] `spec/` — this changes what conformance means
- [ ] `src/` — this changes the reference implementation only
- [ ] Both, and the commits are separate so the record shows which moved first

## Invariants

Confirm none of these is broken, or explain why the change is still correct:

- [ ] No released vocabulary token removed (deprecated with a replacement instead)
- [ ] No released reason code reworded or renumbered
- [ ] No new path that overwrites an observation, event, decision or integrity entry
- [ ] No passport content added to a ledger envelope
- [ ] No unknown value written as zero, empty or a default category
- [ ] The integrity digest still does not depend on who asked

## Evidence

- [ ] `make test` passes
- [ ] `make validate` passes
- [ ] `make example` passes
- [ ] `make openapi` re-run and the result committed, if the API changed
- [ ] A `spec/` change carries a version bump, a changelog entry and a test that failed before it
