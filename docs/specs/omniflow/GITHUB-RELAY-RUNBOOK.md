# GitHub survival relay — executable candidate

Source: [bin/omniflow-github-relay](../../../bin/omniflow-github-relay). Offline tests: [tests/test_omniflow_github_relay.py](../../../tests/test_omniflow_github_relay.py).

## Try from two independent console sessions

Authenticate GitHub with an existing scoped token through the estate vault. Set `GH_TOKEN` or `GITHUB_TOKEN` via the approved runtime, never in a chat, GitHub comment, source file or CLI argument. Both agents must use the same issue and repository. Use an issue authorized for this test, not an unrelated live incident.

Session A:
```bash
python3 bin/omniflow-github-relay --repo chidionyema/idp --issue 7481 --actor console-a send --mission omniflow-canary-1 --kind ASK --text "canary: reply with your agent label and correlation ID"
```

Session B:
```bash
python3 bin/omniflow-github-relay --repo chidionyema/idp --issue 7481 --actor console-b --cursor ~/.estate/omniflow-console-b.sqlite watch --interval 10
```

Session B copies the returned `correlation_id` from the observed event and replies:
```bash
python3 bin/omniflow-github-relay --repo chidionyema/idp --issue 7481 --actor console-b send --mission omniflow-canary-1 --kind ANSWER --correlation CORRELATION_ID --text "received by B"
```

Session A reads:
```bash
python3 bin/omniflow-github-relay --repo chidionyema/idp --issue 7481 --actor console-a --cursor ~/.estate/omniflow-console-a.sqlite read
```

Local offline falsifiers:
```bash
python3 -m unittest discover -s tests -p 'test_omniflow_github_relay.py' -v
```

**Security:** the `actor_label` is explicitly untrusted display data. A GitHub issue comment is never proof of founder/agent identity, lease, effect, execution or authorization. Do not place sensitive user data, credentials, personal screenshots or customer content in this public repo. This prototype is for non-sensitive coordination metadata. Read operations intentionally print `ADAPTER_OBSERVED_UNTRUSTED`; an independent trusted gateway must authenticate, authorize and admit any resulting protected action.

**Durability:** SQLite cursor is per consumer; do not share its database between hosts. The relay handles replay by event ID, rejects conflicting digests and stops on malformed structured events rather than silently skipping them. GitHub comment creation means `GITHUB_ACCEPTED` only. It has no implemented webhook, signed provenance, tenant isolation, NATS reconciliation, end-to-end effect verification or commercial certification yet. It uses polling and obeys GitHub rate-limit errors by surfacing DEGRADED; retry scheduling is basic. The unit suite is pushed but **not verified as executed in the current environment**.

**Operational proof pending:** actual two independent authenticated consoles, issue comment round-trip, failure/restart, malicious actor rejection and reconciliation with NATS. Session C must execute and falsify this code; do not claim the lane operating from source alone.
