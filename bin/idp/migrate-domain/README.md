# migrate-domain

Moves a domain onto Cloudflare without anyone reading a zone file: it asks the nameservers
answering for the domain today what they hold, recreates every record on the new zone, waits
for the nameserver change to take, and can put the old answer back.

Adopted from `survival-stack/scripts` (crew#838 CP1). What changed on the way in: the
credential now comes from the estate's vault instead of the pasteboard and the macOS keychain,
and the checks file was cut down to Cloudflare — the version it came from also checked
Telegram, Hetzner, DigitalOcean, Vultr, Stripe and R2, none of which this tool calls.

## Run it

    # See what the domain holds today. No credential, changes nothing.
    node bin/idp/migrate-domain/migrate-domain.mjs example.com --dry-run --phase=discover

    # The whole move. Reads cloudflare-api-token from the vault.
    node bin/idp/migrate-domain/migrate-domain.mjs example.com

The phases are `discover`, `create`, `records`, `verify`, `cutover` and `confirm`; `--phase=`
runs one of them and `--dry-run` prints what each would do without doing it. The run keeps a
state file, so an interrupted move resumes where it stopped rather than starting over.

## The credential

`CF_API_TOKEN` or `CLOUDFLARE_API_TOKEN` in the environment wins, so a run can be pointed at a
test account; otherwise the root token comes from the vault key `cloudflare-api-token`. The
root is not what the run carries: where the account allows it, the tool mints a token scoped to
that one account with Zone:Edit and DNS:Edit, expiring in an hour, and revokes it at the end
(R52). Nobody is ever asked to mint or paste a credential (LAW 31).

## Tests

    node --test bin/idp/migrate-domain/test/

Nine tests, and CI runs them on any change under `bin/idp/migrate-domain/` (the `migrate-domain`
job in `.github/workflows/ci.yml`). They grade what counts as a Cloudflare credential, that
another vendor's key is never sent to Cloudflare to be verified, and that the minted token is
scoped, time-boxed and revoked with the root rather than with itself.
