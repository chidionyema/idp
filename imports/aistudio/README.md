# AI Studio imports (read-only witness)

Nineteen AI Studio projects, imported byte-for-byte from GitHub on 2026-11-19.

These are **not** a second implementation of anything. Each project is a product that
lives in its own repository; AGENTS.md section 6 says a product is never deleted for
living outside idp, and it also says never leave two of one layer. This directory is
therefore a witness, not a home: nothing here is built, deployed or imported by code.

`MANIFEST.json` records, per repository, the commit that was read and the sha256 of
every file. `verify.py` recomputes both and is the falsifier: a missing byte, an extra
file or a commit that does not match is a refusal.


