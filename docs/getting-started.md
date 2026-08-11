# Getting started

A working passport in about fifteen minutes, then the parts that matter.

## Install and prove it works

```bash
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
python3 -m pip install -e ".[dev]"
make test
make example
```

`make example` is the important one. It runs the worked example from deliverable
D4.3 Annex G end to end and prints a digest. That digest is published in the
deliverable. If it matches, the canonicalisation is correct; if it does not, the
canonicalisation is wrong and nothing built on top of it can be trusted.

## Create a passport

```bash
make serve
```

Then, in another shell:

```bash
curl -sX POST localhost:8000/v1/dpps \
  -H 'Content-Type: application/json' \
  -H 'X-S4C-Role: brand' \
  -H 'X-S4C-Organisation: urn:sort4circ:org:brand-a' \
  -H 'Idempotency-Key: first-passport' \
  -d @examples/fixtures/valid-minimum.json
```

The role header is a development stand-in for a token. It is refused unless
`S4C_ALLOW_HEADER_AUTH` is set, so it cannot leak into a deployment by accident.

## Bind a carrier and resolve it

```bash
DPP=urn:sort4circ:dpp:000001

curl -sX POST "localhost:8000/v1/dpps/$DPP/carriers" \
  -H 'Content-Type: application/json' -H 'X-S4C-Role: brand' \
  -d '{"carrierType":"uhfRfid","encodingScheme":"gs1Sgtin96",
       "encodedIdentifier":"urn:epc:id:sgtin:0614141.112345.400",
       "boundBy":"urn:sort4circ:org:brand-a"}'

curl -s "localhost:8000/v1/identifiers/urn%3Aepc%3Aid%3Asgtin%3A0614141.112345.400/dpp" \
  -H 'X-S4C-Role: pssrSystem'
```

Commissioning is atomic and the identifier is never reassigned. Binding the same
encoded identifier to a second passport returns 409 with
`S4C-IDENT-DUPLICATE-BINDING`, and so does reusing one that was retired.

## Compute a digest without running anything

```bash
python3 -m sort4circ_dpp.cli digest examples/fixtures/valid-annex-g-garment.json --show-projection
```

## Derive the latency budget for a specific line

```bash
python3 -m sort4circ_dpp.cli budget --speed-mps 2.0 --distance-m 3.1
```

The default arguments reproduce the reference configuration in D4.3 and its
920 ms software budget. Substitute the measured parameters of the installed
line. A published latency target that does not come out of this calculation
cannot be justified to anyone who asks how it was derived.

## Where to go next

| Question | Answer |
| --- | --- |
| What fields exist and which are mandatory | `spec/schemas/dpp-1.0.0.schema.json` and D4.3 Annex A |
| What values a coded field accepts | `spec/vocabularies/` |
| What an error means and what the gateway should do about it | `spec/reason-codes.json` |
| Who may see what | `spec/access-matrix.json` |
| What the API does | `spec/openapi/dpp-api-v1.json`, or `/docs` on the running service |
| What conformance means | [`conformance.md`](conformance.md) |
