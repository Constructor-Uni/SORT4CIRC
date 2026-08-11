"""Regenerate the OpenAPI contract from the implemented routes.

The contract is generated rather than hand-written so it cannot drift from the
service. A drift between the two would make the published contract a claim
rather than a description.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sort4circ_dpp.api import create_app  # noqa: E402


def main() -> int:
    document = create_app().openapi()
    document["info"]["license"] = {"name": "Apache-2.0", "identifier": "Apache-2.0"}
    document["externalDocs"] = {
        "description": "SORT4CIRC deliverable D4.3, DPP development guidelines",
        "url": "https://sort4circ.eu",
    }
    target = ROOT / "spec" / "openapi" / "dpp-api-v1.json"
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} with {len(document['paths'])} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
