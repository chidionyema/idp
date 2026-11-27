# Deployment status: NOT FLEET-OPERATIONAL

This candidate preserves existing AGENTS.md and writes its proposed contract to .meridian/context-core.md instead. SHADOW returns ALLOW in both Python and TypeScript; the Python telemetry preserves the proposed directive separately.

Verification: 21 Python tests and 1 TypeScript/Node test passed. The two Python regressions and TypeScript regression were observed failing against the supplied implementation before repair.

No production hooks, routing, credentials, estate instructions, laws or CI enforcement were changed by these candidate repairs. Integration must reuse the existing context compiler and authenticated router ledger. Identity binding, concurrent ledger transactions, gateway recovery, independent live canary and fleet adoption remain required. Enforcement promotion also needs the policy's longitudinal evidence; these tests do not establish it.

Original archive SHA-256: cb13e9f77e046b25eda874c2bbe7cf98a35db5962e11fbc11a43fae4754f58c8
