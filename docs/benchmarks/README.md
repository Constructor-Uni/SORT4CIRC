# Measurements

Deliverable D4.3 states numeric targets. This directory holds the executed
measurements behind them, the harnesses that produced them, and an explicit
statement of what has not been measured and why. A target with no measurement
next to it is a target, not a result, and the two are kept apart here.

Two harnesses live in `tools/`:

| Harness | Measures | Runs where |
| --- | --- | --- |
| `tools/loadtest.py` | the service under concurrent load: resolve, sorting view, observation write, search, outbox drain | any machine with the package installed |
| `tools/anchor_bench.py` | anchoring latency, time to confirmation, fee and metered energy, per ledger platform | a machine with credentials and network access to the platforms under test |

## Load campaign

### Why 920 ms

The sorting path budget is derived, not chosen. The instrumented section of the
conveyor is 2.40 m and the belt runs at 1.5 m/s, so 1600 ms separate the read
from the diverter. The read zone, the plant network and the actuator claim the
remainder, leaving 920 ms for everything the software does between receiving an
identifier and returning a routing answer. The load campaign measures how much
of that 920 ms the reference service consumes.

### Method

`tools/loadtest.py` starts the service under uvicorn on a loopback socket, seeds
passports each with a commissioned UHF carrier, then drives four request classes
at several concurrency levels from separate client threads. Each thread issues
one untimed request first, so TCP setup does not land inside the first sample.
Latency is measured at the client. Percentiles are nearest-rank over the whole
sample, not interpolated.

The four classes are the resolve path that the read zone triggers, the sorting
projection reached by passport identifier, the observation write with its full
validation and digest work, and the paginated collection search.

Reproduce with:

```
python tools/loadtest.py --passports 200 --requests 2000 --concurrency 1,2,4,8 \
    --json docs/benchmarks/loadtest-results.json
```

### What these numbers do not cover

The reference store is in-memory. No database round trip, no disk flush and no
replication delay appears in the figures. They are a floor for the service logic
and not a forecast for a deployment. A deployment that substitutes a relational
store must repeat the campaign and add the storage cost before claiming the
budget is met.

The ledger adapter is in-memory as well, so the outbox drain figure measures the
outbox machinery and states nothing about any chain.

The client and the server share one host over loopback. A plant network adds its
own latency, and that latency belongs to the 1600 ms, not to the 920 ms.

Results are in `loadtest-results.json`, with the environment recorded in the
same document.

For reproducible evidence runs, use CPython 3.12.3, install
`requirements-evidence.txt`, then install the project with
`pip install --no-build-isolation --no-deps -e .`. Compatibility ranges remain
in `pyproject.toml` for ordinary library use. The complete machine-readable
profile is `evidence/environment/reproducibility-profile-1.0.0.json`.

The application image is Python 3.12.14-slim and the optional ledger image is
Besu 26.8.1. The evidence target is explicitly `linux/amd64`; each image records
its OCI index digest, platform-specific manifest digest and image configuration
digest in `evidence/environment/reproducibility-profile-1.0.0.json`. The
Dockerfile and Compose service pin the platform manifests verified against
Docker Hub on 2026-09-03. Host development runtimes are separate from this
Linux evidence environment and are captured per execution record. GitHub
Actions are also pinned to immutable commit SHAs. These pins apply to new
executions and do not retroactively change earlier results.

### Executed campaign

Host: Intel Xeon at 2.10 GHz, 2 cores, 7.8 GiB, Python 3.11.15 on Linux. One
uvicorn process. 200 seeded passports, 2000 requests per class per level.
Latency in milliseconds, measured at the client.

| Class | Concurrency | req/s | p50 | p95 | p99 | max | errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| resolve | 1 | 372 | 2.55 | 3.45 | 5.06 | 31.96 | 0 |
| resolve | 2 | 398 | 4.92 | 6.97 | 8.47 | 16.05 | 0 |
| resolve | 4 | 442 | 8.35 | 13.57 | 17.44 | 49.16 | 0 |
| resolve | 8 | 388 | 18.94 | 31.38 | 53.72 | 94.25 | 0 |
| sortingView | 1 | 313 | 2.16 | 5.78 | 17.68 | 596.97 | 0 |
| sortingView | 2 | 418 | 4.65 | 6.94 | 8.57 | 12.14 | 0 |
| sortingView | 4 | 405 | 9.36 | 13.60 | 18.77 | 129.75 | 0 |
| sortingView | 8 | 428 | 18.12 | 25.23 | 31.00 | 56.75 | 0 |
| observation | 1 | 167 | 5.86 | 7.64 | 10.08 | 54.69 | 0 |
| observation | 2 | 121 | 16.12 | 23.31 | 26.26 | 82.56 | 0 |
| observation | 4 | 88 | 43.81 | 63.59 | 79.26 | 156.92 | 0 |
| observation | 8 | 72 | 107.79 | 147.93 | 248.18 | 302.58 | 0 |
| search | 1 | 8.6 | 96.42 | 265.26 | 287.62 | 311.46 | 0 |
| search | 2 | 7.8 | 219.42 | 405.05 | 444.98 | 540.72 | 0 |
| search | 4 | 7.8 | 513.35 | 712.41 | 814.96 | 1819.43 | 0 |
| search | 8 | 7.6 | 1049.57 | 1351.42 | 1501.14 | 1773.22 | 0 |

Outbox drain: 8415 entries in 196 ms, 0.023 ms per entry, all confirmed; a
rescan of the drained queue costs 6 ms.

### What the campaign says

The sorting path is not where the budget goes. Resolve consumes 5.06 ms at p99
with one caller and 53.72 ms at p99 with eight on two cores, against 920 ms. The
budget is spent elsewhere: in the read zone, in the plant network, in the
actuator, and in whatever database replaces the reference store.

Throughput on the read paths is flat from one to eight concurrent callers at
roughly 400 requests per second, which is the two-core saturation point of a
single Python process. Latency scales linearly with concurrency past that point,
as queueing predicts. A pilot line reads one garment at a time; the concurrency
levels here describe several lines against one service instance.

The write path costs more than the read path and degrades faster: 167 requests
per second at one caller, 72 at eight. Each write validates the payload against
the schema and the vocabularies, checks the composition rule per observation set,
increments the version, recomputes the digest over the full integrity projection
and commits an outbox entry. The digest is recomputed over every observation the
record carries, so a record accumulating observations gets more expensive to
write. That is a property of the integrity design, not an implementation defect,
and it bounds how many observations a single passport should accumulate before a
deployment considers segmenting the projection.

The single 597 ms maximum on the first sorting-view level is the first request to
touch that code path in a fresh process. It appears once in 32000 requests and
does not recur at any other level. A pilot deployment removes it by issuing a
warm-up request before the line starts.

### Two defects the campaign exposed

**The projection refused to serve a quiet line.** The read index bounded the
wall-clock age of a projection against a 30 s staleness limit. On a line that
paused for longer than that, every sorting read failed with
`S4C-DEP-UNAVAILABLE` until the next write: in the first campaign, 395 failures
at concurrency 2 and 2000 out of 2000 at concurrency 4 and 8. A projection that
nothing has invalidated is current, not stale. The limit now bounds the interval
by which the projector trails the source, which is what the limit was for; the
store records the time of its most recent commit and the projector records the
moment it last caught up. `tests/test_index_staleness.py` covers both cases: a
quiet line is served, a projector that stopped while writes continued is refused.
No functional test had reached this, because functional tests write and read
within milliseconds.

**Collection search does not scale.** Search sorts the entire collection on every
request and projects 50 full records: 8.6 requests per second at one caller, and
a p99 of 1501 ms at eight. It is the only class in the campaign that misses a
sub-second p99. The reference store keeps records in a dictionary and has no
ordered structure to page over, so the ordering is rebuilt per request. Ordering
and pagination belong in the database index of a deployment, which is the
substitution the store already documents. The figure is recorded here so that the
substitution is understood as required and not optional. Search is not on the
sorting path and this does not affect the 920 ms budget.

## Anchoring benchmark

`tools/anchor_bench.py` benchmarks any set of platforms that implement the
adapter contract in `sort4circ_dpp.ledger.base`. Each platform is added by
writing an adapter and one configuration entry. Every platform anchors the same
871-byte canonical projection, so payload size is not a variable between them.

Per platform the harness records submission latency, time from submission to
confirmation, the fee when the adapter receipt carries one, the count of
submissions that never confirmed inside the timeout, and the reason code of every
failure. After each confirmation it re-verifies the anchored digest, because a
platform that confirms quickly and returns a different digest is a failure and
not a fast platform.

A platform that cannot be reached, or whose adapter cannot be loaded, is reported
as `notReached` and contributes no figures. There is no modelled fallback and no
substitution of a published average. A benchmark that fills its gaps with
literature values cannot be distinguished afterwards from one that measured them.

Verify the harness itself without any network:

```
python tools/anchor_bench.py --self-test
```

The self test anchors against the in-memory adapter and prints the reference
digest `dd14a3f2...` over an 871-byte payload, which is the same value published
in D4.3 Annex G. Its latency figures describe the process and nothing else, and
the output says so.

Run a real campaign:

```
python tools/anchor_bench.py --config anchor-targets.json --runs 50 \
    --json docs/benchmarks/anchor-results.json
```

`anchor-targets.example.json` is a starting configuration covering the
permissioned Besu network and four public platforms.

### Energy

Energy per anchored record is computed from a meter log, never from a model. The
harness needs two logs of `timestamp_iso8601,watts` samples: one covering the
campaign, and one covering the same hardware, idle, with the service stopped. The
idle log is not optional, because the quantity of interest is the marginal energy
of anchoring and not the standing draw of the machine. Given both, the harness
integrates each log, subtracts the idle baseline over the campaign duration, and
divides the remainder by the number of confirmed anchors.

```
python tools/anchor_bench.py --config anchor-targets.json \
    --energy-csv meter.csv --energy-idle-csv idle.csv
```

Without both logs the energy section reports `notMeasured` together with the
reason. The scope of any figure it does report is the submitting node. Energy
consumed by validators, and network-wide energy per transaction, are not
measurable from a client and are not reported. A statement about those belongs to
a study with access to the validator set, and citing such a study is a literature
statement, not a result of this harness.

## Status of the four public platforms

As published, this repository contains executed results for the load campaign and
for the harness self test only. Results for EBSI, Algorand, IOTA and Ethereum are
absent because the measurement requires credentials, network placement and a
meter that the publishing environment did not have. The harness is complete and
the configuration is written; what is missing is the run.
