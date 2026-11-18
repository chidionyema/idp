# Add or change a model

The founder-facing rule is: **one provider connection once, one model block per
version, one alias the clients ask for**.

Open your live route board at `http://127.0.0.1:4100/dash`. It shows each client
name, the exact provider/model lane it resolves to, its context window and the
declared fallback order. A route is working only when a real call appears there.

## Change a model version

Edit the existing `[[models]]` block. Do not add Rust.

```toml
[[models]]
id = "glm-5.3"
class = "paid"
price_in_per_mtok = 0
price_out_per_mtok = 0
context_window = 200000
aliases = ["glm"]
fallbacks = ["minimax/MiniMax-M3.1-Flash", "deepseek/deepseek-chat"]
```

The `id` is the exact upstream model version. `aliases` are the stable names
clients use. If the provider changes the version, change `id`; clients keep
asking for `glm`.

## Add an OpenAI-compatible provider

Provider files are connection contracts, not routing policy. Every field is
mandatory so nothing is inferred from a URL:

```toml
id = "provider-name"                  # must equal provider-name.toml
dialect = "openai"                    # openai or anthropic
base_url = "https://api.example.com"  # origin/API root, no inferred version
request_path = "/v1/chat/completions" # EXACT path appended to base_url
api_key_file = "/run/secrets/pennyd/provider-name/PROVIDER_API_KEY"

[auth]
kind = "bearer"
key_env = "PROVIDER_API_KEY"

[[models]]
id = "exact-upstream-model-id"
class = "paid"
price_in_per_mtok = 1.0
price_out_per_mtok = 2.0
context_window = 128000
aliases = ["friendly-name"]
```

If the provider's real endpoint is
`https://api.example.com/v4/chat/completions`, declare:

```toml
base_url = "https://api.example.com/v4"
request_path = "/chat/completions"
```

There is deliberately no `/v1` or `/v4` guessing in code.

## Agent checks

```bash
make provider-check
```

This runs the provider contract test plus the complete workspace suite. A
provider without a valid dialect, exact request path, auth declaration, unique
model ID or unique alias fails registry load.

Every provider boundary change must update `FAILURE_MODES.md` with its `F-PV-*`
row, the exact failing test and the founder-visible recovery.
