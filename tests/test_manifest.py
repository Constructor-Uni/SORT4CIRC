"""Manifest completeness is defined by the explicit public policy."""
from pathlib import Path

from tools.verify_public_release import verify_tree


def test_manifest_matches_public_candidate():
    assert verify_tree(Path(__file__).resolve().parents[1], workspace=True) > 0
