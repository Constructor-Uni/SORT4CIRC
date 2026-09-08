"""Vocabulary release integrity."""

from __future__ import annotations

import json

import pytest

from sort4circ_dpp.config import VOCAB_DIR
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.vocab import FIELD_VOCABULARIES, load, published


@pytest.mark.parametrize("name", published())
def test_every_vocabulary_declares_its_release_metadata(name):
    doc = json.loads((VOCAB_DIR / f"{name}.json").read_text(encoding="utf-8"))
    assert {"$id", "name", "version", "released", "owner", "terms"} <= set(doc)
    assert doc["name"] == name
    assert doc["terms"], "an empty vocabulary cannot constrain anything"


@pytest.mark.parametrize("name", published())
def test_tokens_are_unique_within_a_vocabulary(name):
    tokens = [term["token"] for term in json.loads((VOCAB_DIR / f"{name}.json").read_text())["terms"]]
    assert len(tokens) == len(set(tokens))


@pytest.mark.parametrize("name", published())
def test_a_deprecated_token_names_its_replacement(name):
    vocabulary = load(name)
    for token in vocabulary.deprecated:
        assert vocabulary.replacements[token], f"{name}:{token} is deprecated without a replacement"


def test_an_undeclared_token_is_refused():
    with pytest.raises(DppError) as excinfo:
        load("article-class").validate("sweater", "product.articleClass")
    assert excinfo.value.code == "S4C-PAYLOAD-VOCAB-INVALID"


def test_every_coded_field_names_a_published_vocabulary():
    for path, vocabulary in FIELD_VOCABULARIES.items():
        if not vocabulary:
            continue
        assert vocabulary in published(), f"{path} names unpublished vocabulary {vocabulary}"


def test_manual_review_is_always_available_as_a_sorting_outcome():
    """A rule set with no safe outcome routes ambiguous items incorrectly."""
    assert "manualReview" in load("sorting-category").tokens


def test_unknown_and_not_measured_remain_distinct():
    tokens = load("value-status").tokens
    assert {"supplied", "notMeasured", "unknown", "notApplicable", "withheld"} <= tokens


def test_legal_fibre_names_are_carried_for_regulated_terms():
    doc = json.loads((VOCAB_DIR / "fibre-type.json").read_text())
    cotton = next(t for t in doc["terms"] if t["token"] == "cotton")
    assert cotton["legalName"] == "Cotton"
    assert "1007/2011" in doc["note"]
