# Regulatory context and limits

What this profile is, what it is not, and where the boundary sits.

## What it is

A technical implementation profile: a data model, controlled vocabularies, representations,
an exchange contract, an access model, an optional integrity profile, and a reference
implementation. It helps developers and organisations design and build a textile Digital
Product Passport, and gives them a way to test what they built.

## What it is not

"Normative" describes only the public-profile rules versioned in this repository. Profile
conformance is distinct from legal or regulatory conformity.

This repository does not constitute an official European Union specification, European
Commission certification or CEN/CENELEC certification. It provides no legal advice, no
proof of ESPR conformity and no proof of a deployment's legal compliance. Nobody issues,
and nobody recognises, a certificate against this profile.

It also does **not** determine which obligations apply to your product or organisation.
That depends on your products, markets, role in the supply chain and the applicable legal
instruments and their timing — none of which a repository can assess.

## Requirement origins

[Traceability](traceability.md) classifies every requirement area by origin:
**standards-profile**, **SORT4CIRC project-scope**, or **SORT4CIRC engineering/architecture
decision**.

Deliberately, **no row is classified as a legal obligation.** Rules here derive from
technical standards the profile adopts, from the use cases SORT4CIRC addresses, and from
architecture decisions. Where the profile is demanding — mandatory provenance on every
observation, thirteen mandatory members on an environmental value — that is engineering and
project-scope reasoning about what makes data usable, not an assertion that the law
requires it.

## Standards references

Standards named in this repository — JSON Schema 2020-12, RFC 3339, RFC 8785, RFC 9457,
XSD 1.1, OWL 2 DL, SHA-256, and the GS1 encoding schemes named in the `encoding-scheme`
vocabulary — identify external specifications. Naming one is not a claim of full conformity
with it, and this repository redistributes and relicenses none of them.

Where the profile adopts a subset or records a deviation, it says so rather than
overclaiming. Two examples:

- the canonicaliser implements the restricted numeric and Unicode behaviour its code and
  tests document, and rejects inputs outside that range instead of serialising them in a
  form another implementation might not reproduce. It is not a general certification of
  every possible RFC 8785 input;
- the ontology declares **OWL 2 DL** and states explicitly that the EL subset is excluded,
  because the disjointness and asymmetry axioms the model relies on are not expressible in
  EL.

Vocabulary labels and references are contextual information, not an assessment of
completeness or applicability.

## What a passing test run establishes

Exactly what was tested, against the code that ran it. It is not physical-line validation,
industrial validation, proof of durability, a performance guarantee, comprehensive security
assurance, or legal or regulatory conformity. See [Conformance](conformance.md).

## What to do instead

Evaluate the applicable requirements for your product and organisation independently, with
appropriate legal and technical expertise. Use this profile for the engineering: the data
model, the identifiers, the provenance discipline, the interfaces and the tests. Use it as
a foundation you can point at when explaining what your implementation does — not as
evidence that it satisfies a legal obligation.

## Related pages

- [Traceability](traceability.md) — requirement origins and implementation status
- [Conformance](conformance.md) — what is machine-testable and what is not
- [PUBLICATION_BOUNDARY.md](../PUBLICATION_BOUNDARY.md) — what is and is not published here
