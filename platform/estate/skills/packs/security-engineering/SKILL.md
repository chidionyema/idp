---
name: security-engineering
description: "Security engineering skills: attack-tree construction, STRIDE analysis patterns, security-requirement extraction, SAST configuration and threat-mitigation mapping. Use when a change touches authentication, secrets, supply chain, input handling or the cluster's trust boundary."
license: MIT
metadata:
  estate-category: security
  estate-upstream: wshobson/agents
---

# Security engineering -- threat modelling, requirements, SAST configuration

Threat modelling as a repeatable craft: attack trees, STRIDE analysis, security requirements extracted from the design, SAST configuration, and a mitigation map that ties each threat to its control.

## When to use this

Before a change lands in the trust boundary: anything that authenticates, holds a
secret, takes input, ships an image or changes what an agent may do.

## How to use it

1. `upstream/plugins/security-scanning/skills/attack-tree-construction/SKILL.md` - the attack surface.
2. `.../stride-analysis-patterns/SKILL.md` - the classification of each path.
3. `.../security-requirement-extraction/SKILL.md` - requirements the design implies.
4. `.../sast-configuration/SKILL.md` - make the scanner say something true.
5. `.../threat-mitigation-mapping/SKILL.md` - the control for each threat, named.

The estate's `estate-secrets`, `break-glass` and `security-scan` intents are the
controls; this pack is how the threats against them are found.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `wshobson/agents` at commit `0874a27b17a22e2b7c2e2bcd725768e0803cad06`
(MIT, 41619 stars at 2026-10-24T08:03:08+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/plugins/security-scanning/skills/attack-tree-construction/SKILL.md`
- `upstream/plugins/security-scanning/skills/sast-configuration/SKILL.md`
- `upstream/plugins/security-scanning/skills/security-requirement-extraction/SKILL.md`
- `upstream/plugins/security-scanning/skills/stride-analysis-patterns/SKILL.md`
- `upstream/plugins/security-scanning/skills/threat-mitigation-mapping/SKILL.md`

<!-- provenance:end -->
