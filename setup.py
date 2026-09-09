"""Bundle only explicitly allowed public package and specification files."""
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

# A PEP 517 backend does not guarantee that the project root is importable, so the
# release policy helpers below must be reachable however the build was invoked.
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class BuildWithSpec(build_py):
    def run(self):
        from tools.verify_public_release import ReleaseError, file_set, leakage, load_policy
        root = Path(__file__).resolve().parent
        policy = load_policy(root)
        expected = {p for p in policy["files"] if p.startswith(("src/sort4circ_dpp/", "spec/"))}
        present = set()
        for name in ("src/sort4circ_dpp", "spec"):
            present |= {name + "/" + p for p in file_set(root / name, workspace=True)}
        if present != expected:
            raise ReleaseError("package source policy mismatch")
        for name in expected:
            leakage(name, (root / name).read_bytes(), policy)
        super().run()
        target = Path(self.build_lib) / "sort4circ_dpp" / "spec"
        for name in sorted(expected):
            if name.startswith("spec/"):
                output = target / name[len("spec/"):]
                self.mkpath(str(output.parent))
                self.copy_file(str(root / name), str(output))

class PublicSourceDistribution(sdist):
    def initialize_options(self):
        super().initialize_options()
        self.formats = ["gztar"]

    def make_distribution(self):
        from tools.verify_public_release import normalise_source_archive
        if self.formats != ["gztar"]:
            raise ValueError("public source distributions require the verified gztar format")
        super().make_distribution()
        for name in self.archive_files:
            normalise_source_archive(Path(name))

setup(cmdclass={"build_py": BuildWithSpec, "sdist": PublicSourceDistribution})
