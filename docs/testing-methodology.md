# Local testing methodology

Synthetic example. Not SORT4CIRC project data.

Construct inputs with SyntheticFixtureFactory. Choose and record your own request count and operations before measuring. tools/loadtest.py runs a small in-process API workload using only fictional records; it cannot measure a network or a deployment. tools/anchor_bench.py checks mock integrity behaviour and does not benchmark a real ledger.

For a local latency experiment use python tools/loadtest.py --requests 12. A user-selected --output path can retain that user's result privately outside the public candidate. The script counts failures and computes latency percentiles from the user's own run. A target is a requirement chosen before execution; an observed value is a measurement. The tool supplies no target and this repository contains no recorded results.

Record the relevant interpreter, dependency versions, workload, machine resources, warm-up and measurement method in your private lab notes. Do not automatically publish environment records. Compare repeated runs only under an explicitly documented method. Short in-process measurements have scheduling noise and exclude network, persistence and external integrity costs.

PublicConformanceSummary exports only allowed status fields. It is not a raw capture mechanism. Review any result you independently choose to publish and keep paths, identities, endpoints, secrets and private data out of it.
