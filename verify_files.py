"""Regenerate hashes only for the explicit public file set in the release policy."""
import argparse

from tools.verify_public_release import ROOT, ReleaseError, verify_tree, write_manifests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.write:
            write_manifests()
        count = verify_tree(ROOT, workspace=True)
        print(f"Public manifest verified ({count} files).")
        return 0
    except (ReleaseError, OSError, ValueError, KeyError):
        print("Public manifest verification failed; review policy and content privately.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
