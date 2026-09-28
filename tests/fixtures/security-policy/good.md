# Security policy

**Owner:** the founder (chidionyema). **Scope:** every repository under the estate
account, every image the estate publishes, every host it runs on, every secret it
holds. **Review:** each row is re-run by `bin/idp-ci` on every pull request and by
`bin/idp-verify` on the live estate; this page is re-read at every quarterly review
and whenever a row changes. **Standard we measure against:** ISO/IEC 27001:2022
Annex A controls, named per row, because that is the checklist a buyer's engineer
brings. `bin/security-policy-gate` refuses this page if any control row lacks a
proof command that exists.

A control is a claim. The proof column is the command whose output makes it true.
A row whose proof prints FAIL or BLIND is an open incident, not a policy.

## Controls

| Control | ISO 27001 | Proof command | State on 2026-08-25 | Gap |
|---|---|---|---|---|
| Ports declared | A.8.20 | `bin/port-gate` | ok | none |
