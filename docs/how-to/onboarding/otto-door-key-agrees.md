# Onboarding: otto-door-key-agrees

## What it is for

Otto reaches a model through a lifeboat sidecar, not directly. `bin/idp-otto-door-key-agrees`
proves that the key the door presents is one that lifeboat can validate. If the two disagree,
Otto goes silent on every message while every health check stays green, so this gate is the
thing standing between a working assistant and a day of that.

## When it runs

On every pull request, as the `ottodoorkey` row of `rules.yaml`, and on a session hook whenever
`platform/otto-gateway/deployment.yaml` is edited. Run it by hand the same way:

```
python3 bin/idp-otto-door-key-agrees [path/to/deployment.yaml]
```

Exit `0` means they agree, or the door does not talk to the sidecar at all. Exit `1` means they
disagree and Otto would be mute. Exit `2` means the file could not be read or parsed.

## What to do when it goes red

The message names both sides. There are three shapes.

*The door presents `LITELLM_API_KEY` unhashed.* The sidecar derives its master key as
`sk-$(printf '%s' "$KEY" | sha256sum | cut -c1-40)`; the door must derive it the same way from
the same mounted file before exporting it. Do not mint a second secret to hold the master key —
the derivation exists so there is one credential and one rotation, not two.

*The two read different Secrets.* One of the containers has had its `volumeMounts` or the
`volumes:` block changed so that its copy of `LITELLM_API_KEY` now comes from somewhere else.
Point them back at the same volume. The same formula over two different values is still a key
the lifeboat refuses.

*The key cannot be resolved to a Secret at all.* A mount was renamed, or a volume lost its
`secret:` source. A key whose origin cannot be read cannot be proved to match, so the gate
fails closed rather than guessing.

## What it does not check

It does not check that the key *works* — only that both containers agree on which one it is.
Whether MiniMax accepts the value behind it is a live question, and the answer-probe is what
asks it.

## Fixtures

`tests/fixtures/otto-door-key/bad.yaml` is the deployment exactly as it ran on 2026-09-10,
refusing every real turn. `tests/fixtures/otto-door-key/good.yaml` is the same file with the
one line that fixes it. Both run in CI, so the gate is proved in both directions on every pull
request rather than only on the day it was written.

**Door (from the UI):** Backstage → Catalogue → `otto-gateway` → CI checks, row `ottodoorkey`.
