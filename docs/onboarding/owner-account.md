# Onboarding: owner-account

## What it is

`docs/reference/owner-accounts.yaml` lists each provider with its login identity, second owner,
recovery route and what the estate uses it for. Identities are labels such as `founder-gmail`,
never addresses, so the file is safe to hand to a buyer. `bin/owner-account-gate [FILE]` grades it.

## Why it exists

Risk R13 in the crew register: one Google account is the login and the recovery route for
GitHub, Oracle Cloud, Cloudflare, Stripe, Anthropic, OpenRouter and the Apple ID. Lose the
mailbox and every provider goes with it, and nothing comes back because recovery lands in the
same place. A buyer cannot take ownership of anything without being handed one personal account.

## How a row closes

Add a second owner identity at the provider (an organisation owner, a break-glass user, or the
buyer's own identity) and move recovery to a hardware key, then change the row in the same pull
request as the provider's own audit log entry. The gate turns green at 0.
