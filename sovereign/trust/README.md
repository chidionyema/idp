# sovereign/trust — HardwareTrustAnchor (cp20), owner: builder D
One interface, four backends: `secure_enclave` (macOS CryptoKit via
`presence_helper.swift`, compiled once into `$ESTATE_HOME/bin/estate-presence`),
`windows_hello` (winrt, guarded import), `fido2` (guarded import),
`software_key` (0600 HMAC file, always available). `trust.backend="auto"`
drives the one `platform.system()` call in `anchor.py` — nowhere else in
`sovereign/` branches on the OS (cp20).

Run: `python -c 'from sovereign.trust import HardwareTrustAnchor; print(HardwareTrustAnchor().backend)'`
Prove: `sovereign/.venv/bin/python -m unittest sovereign.trust.test_trust -v`
       `grep -rln 'platform.system\|sys.platform' sovereign --include=*.py --exclude-dir=.venv`

## Two blocks A adds to `sovereign/config.py`, after the COCKPIT_KEYS block
```python
try:
    from sovereign.trust.config_keys import TRUST_KEYS
    _merge_external_keys(TRUST_KEYS)
except ImportError:
    pass
try:
    from sovereign.attach.config_keys import ATTACH_KEYS
    _merge_external_keys(ATTACH_KEYS)
except ImportError:
    pass
```
Circular-import-safe (verified in an isolated copy): `anchor.py` never
imports `sovereign.config` at module level, only lazily inside a method.
`trust.backend` is already in `KEYS`; `TRUST_KEYS` adds only what's beyond it.

## Three lines A adds to `sovereign/engine/receipts.py` for `--signed`
```python
from sovereign.trust import HardwareTrustAnchor   # top-level import
# inside append(), after line["hash"] = line_hash, before the file write:
if record.get("signed"):
    line["hw_sig"], line["hw_backend"] = HardwareTrustAnchor().sign(line_hash)
```
`cli.py`'s `--signed` sets `record["signed"] = True` before calling append.

**Residual:** `windows_hello`/`fido2` `.sign()` has no signing path, falls
back to `software_key` honestly. The enclave Keychain item has no
access-control policy yet — `sign()` doesn't force a prompt, though
`verify_founder_presence()` does (real one). cp14 scope.
