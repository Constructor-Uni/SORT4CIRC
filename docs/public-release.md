# Public release verification

The public-release-policy.json file lists every permitted source file explicitly. Confidential targeted indicator rules and exact attribution exceptions are supplied separately from a private file outside the checkout. The public policy contains no fingerprints derived from private records. Review policy changes; do not automatically allow every file found in a checkout.

Run python verify_files.py --write after an approved source change. This updates MANIFEST.in and MANIFEST.sha256 within the existing file policy. Run python tools/verify_public_release.py --files-only to check public source contents, hashes and Docker inclusion rules. This explicitly does not run the private indicator scan.

A working checkout may retain private local review files, ignored raw evidence and caches. The workspace check deliberately excludes those local-only locations. It does not make the checkout or its Git history safe to publish.

Create a fresh public export outside the checkout:

~~~sh
python tools/verify_public_release.py --private-rules ../private-indicator-rules.json --export ../public-profile-export
python tools/verify_public_release.py --private-rules ../private-indicator-rules.json --candidate ../public-profile-export
~~~

The final-candidate check permits no extra files, including caches, private reviews, raw evidence, local configuration or archive files. It never depends on .gitignore. Keep build output outside the export. Check a built source archive or wheel with --archive followed by its path, together with --private-rules. A run with neither --private-rules nor the explicit --files-only limitation fails. CI checks file policy only; a release reviewer must run the confidential indicator scan separately. The archive verifier rejects unexpected entries, path traversal, links, changed payloads and unapproved metadata. Generated documentation sources and the static SVG are part of the exact file policy; any generated site must receive its own reviewed policy before publication.

The Docker context starts with a deny-all .dockerignore and permits only explicit public build inputs. Use docker compose -f docker/compose.example.yml up --build for the optional local demo. Image construction needs the user's chosen local build environment and dependencies; it is not a reproducibility or production claim.

Passing these checks means the current candidate satisfies this file policy. Licence coverage is recorded in LICENSING.md. Passing this file-policy check does not resolve the security reporting channel, history remediation or human publication approval.

Private rules contain indicatorTokenHashes (SHA-256 of case-folded alphanumeric token sequences joined by spaces), maxIndicatorTokens and attributionAllowlist entries with path, lineHash and indicatorHash. lineHash binds an exception to the exact UTF-8 line without its newline. Prepare and retain those rules privately from the authorised audit. Do not commit them, their source values or derived record fingerprints. Tests use invented markers only.

Source distribution generation removes local owner/group names, numeric ownership, timestamps, PAX fields and gzip header metadata. Only the verified gzip/tar source format is supported. Archive verification rejects non-neutral source headers as well as unsafe contents; normalization does not alter file payloads or licences.
