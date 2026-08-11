"""The delivered manifest describes the delivered tree.

A manifest that has fallen behind the tree is a delivery defect, not a
housekeeping detail: the verifier a reviewer runs is the evidence that a
checkout is what was published, and it fails on a correct checkout once the
manifest is stale. Asserting it here makes regeneration a test failure with the
offending paths named, rather than something a person has to remember.

The scan is not reimplemented. It is imported from ``verify_files`` so that this
test and the verifier can never disagree about which files are covered.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("verify_files", ROOT / "verify_files.py")
verify_files = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_files)


def test_manifest_lists_every_delivered_file_with_a_matching_digest():
    manifest = ROOT / verify_files.MANIFEST_NAME
    if not manifest.exists():
        pytest.fail(f"{verify_files.MANIFEST_NAME} is missing from {ROOT}")

    expected = verify_files.read_manifest(manifest)
    present = verify_files.scan(ROOT)
    missing, changed, extra = verify_files.compare(expected, present)

    problems = []
    if missing:
        problems.append(
            f"listed in the manifest but absent from the tree ({len(missing)}):\n  "
            + "\n  ".join(missing)
        )
    if changed:
        problems.append(
            f"content does not match the recorded digest ({len(changed)}):\n  "
            + "\n  ".join(changed)
        )
    if extra:
        problems.append(
            f"present in the tree but not listed in the manifest ({len(extra)}):\n  "
            + "\n  ".join(extra)
        )

    if problems:
        pytest.fail(
            f"{verify_files.MANIFEST_NAME} does not describe this tree. "
            "Regenerate it with: python verify_files.py --write\n\n"
            + "\n\n".join(problems)
        )


def _git_ls_files() -> set[str] | None:
    """Tracked paths according to git, or None when this is not a usable checkout.

    A released archive is not a clone, which is the case the manifest exists to
    serve, so the absence of git is a skip and never a failure.
    """
    if not (ROOT / ".git").exists() or shutil.which("git") is None:
        return None
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    # -z avoids git's quoting of unusual characters, so paths arrive verbatim.
    return {p for p in result.stdout.decode("utf-8").split("\0") if p}


def test_the_walk_covers_exactly_what_git_tracks():
    """The scan and .gitignore must not drift apart.

    ``scan`` deliberately walks the filesystem rather than asking git, because a
    reviewer may receive a folder that is not a clone and the manifest still has
    to verify it. That independence is the point, and it is also the risk: an
    ignore rule added to one and not the other goes unnoticed until the verifier
    reports a file nobody meant to deliver, or silently omits one. Inside a
    checkout the two definitions are comparable, so they are compared.
    """
    tracked = _git_ls_files()
    if tracked is None:
        pytest.skip("not a git checkout, or git is unavailable")

    # The manifest cannot contain its own digest, so it is tracked but never
    # scanned. It is the one permitted difference between the two sets.
    tracked -= {verify_files.MANIFEST_NAME}
    walked = set(verify_files.scan(ROOT))

    untracked = sorted(walked - tracked)
    unwalked = sorted(tracked - walked)

    problems = []
    if untracked:
        problems.append(
            f"the walk covers files git does not track ({len(untracked)}); either commit "
            f"them or add an ignore rule to both .gitignore and verify_files.py:\n  "
            + "\n  ".join(untracked)
        )
    if unwalked:
        problems.append(
            f"git tracks files the walk excludes ({len(unwalked)}); an ignore rule in "
            f"verify_files.py is hiding a delivered file:\n  " + "\n  ".join(unwalked)
        )

    if problems:
        pytest.fail(
            "the manifest walk and the tracked file set have diverged.\n\n"
            + "\n\n".join(problems)
        )
