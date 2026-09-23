# DeepSeek as the cheap build lane

Founder, 2026-09-03, verbatim: "use deepseek for cheap build." Graded by
`tests/test_llm_row.py::test_build_alias_names_the_cheap_build_lane`,
`test_build_alias_falls_back_to_the_other_funded_cheap_lane` and
`test_deepseek_reasoner_row_shares_the_deepseek_account`.

## What changed

The router already had a `deepseek` row (`deepseek/deepseek-chat`) and its own key. This adds
two more rows on that same DeepSeek account, in `platform/vendors/consoles.yaml` (the one file
allowed to name a model vendor; no other file in the estate ever names one) and rendered by
`bin/idp-vendor-render` into both `llm/config.yaml` (the developer's local mirror) and
`platform/llm/config.yaml` (the cluster):

- **`build`.** A capability name, not a vendor name, the same pattern as `vision` on the Gemini
  row. A worker that does executor work asks the router for `build` and lands on
  `deepseek/deepseek-chat`, and its own code never names DeepSeek. If DeepSeek answers a
  failure, the router falls back to `minimax`, the other funded cheap lane, so a build turn does
  not fail outright.
- **`deepseek-reasoner`.** DeepSeek's thinking-mode model on the same account, for callers that
  ask for it by name.

## No new founder step

Both new rows read the same environment variable the existing `deepseek` row already reads,
`os.environ/DEEPSEEK_API_KEY`, from the same vault entry, `litellm-upstream`
(`platform/llm/external-secret.yaml`). No new area of that vault entry was added, so this change
needs no new key and no repeat of the one-time step below.

## The one founder step, only if the DeepSeek root is ever missing

This is the step that put the account's key in the vault in the first place
(`platform/vendors/consoles.yaml`, vendor `deepseek`: `page:
https://platform.deepseek.com/api_keys`, `secret: SEED_DEEPSEEK_API_KEY`). Every vendor
credential on the estate follows the same rule: the founder makes the key once, by hand, at the
vendor's own page, and sets it as one repository secret. Code does everything after that. It
does not go through `vault-seed.yml`. That workflow's own choice list does not offer a vendor
key, and its own script refuses one by name and points at the step below
(`.github/workflows/vault-seed.yml:87`, function `retired()`):

```
echo "bin/idp-estate-seed (estate keys), bin/idp-bootstrap-vendors (vendor keys), bin/idp-bootstrap-cloudflare (R2), bin/idp-github-app refresh (GitHub tokens)"
```

The two commands, run from a phone or a laptop, no cluster access needed for either:

```
gh secret set SEED_DEEPSEEK_API_KEY -R chidionyema/idp
gh workflow run oke-check.yml -f mode=apply -R chidionyema/idp
```

That run's `bin/idp-bootstrap-vendors (crew#579, R52)` step
(`.github/workflows/oke-check.yml:263`) reads `SEED_DEEPSEEK_API_KEY`
(`.github/workflows/oke-check.yml:271`), proves it against DeepSeek's own API, and writes it into
`litellm-upstream` as `DEEPSEEK_API_KEY`; a key the vault already holds that still proves out is
kept as is, so this step is safe to run again and the repository secret may be deleted once the
run is green.

## Checking it

`GET https://llm.<zone>/v1/models` with a router key lists `build` and `deepseek-reasoner`
alongside every other row. `platform/llm/config.yaml` is generated; a hand edit to it, or a
registry edit with no re-render, fails `bin/idp-vendor-render --check` (run by `bin/idp-ci`).
