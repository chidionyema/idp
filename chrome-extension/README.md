# chrome-extension — the Meridian Web Membrane

Pre-render quarantine and a deterministic egress gate for consumer web AI agents
(Gemini, ChatGPT, Claude, AI Studio). No LLM inside: six hard gates, a trust card
or a rejection banner, computed on device.

Source of truth: this directory. The release and signing repo is
`chidionyema/meridian-membrane`, which holds the CRX build, the Cloudflare
verifier, the install tooling and the adversarial suite.

Verification: 11/11 adversarial vectors in real Chrome 158 V8 (receipt
cd6bd58da1e4b4a4) and 11/11 under Node. Not yet observed on an authenticated
vendor DOM.
