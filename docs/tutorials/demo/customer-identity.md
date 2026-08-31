# Demo: Nobody can quietly change who may sign in to the shop

Sign-in settings are the one part of a shop that a person can change in ten seconds from an
administration screen, and that nobody would ever notice. Turn off the lock-out after five wrong
passwords. Make a sign-in last a day instead of five minutes. Add one more address the shop is
allowed to send a signed-in customer back to. Each of those is a single click, none of them shows
up in the shop, and all three are how accounts get taken.

This is the answer to that, and every command below runs on a laptop with no cluster.

## The rules are a file, not a screen

```
$ grep -E '^(realm|bruteForceProtected|failureFactor|accessTokenLifespan|verifyEmail):' platform/customer-identity/realm/shop.yaml
realm: shop
verifyEmail: true
bruteForceProtected: true
failureFactor: 5
accessTokenLifespan: 300
```

Twenty-seven settings and two applications, in git, reviewed in a pull request like anything
else. No address is typed into it, so the same file is the truth for the live shop and for a
practice copy.

## What is running is graded against that file

The shop's own web address is the one thing the file does not name, so hand it to the check
once. Nothing else is needed: the shop's application password is graded by whether it is there
at all, so the check never asks for it and never holds one.

```
$ export SHOP_ORIGIN=https://shop.mumchimp.com
$ export SHOP_REDIRECT_URI=https://shop.mumchimp.com/api/auth/callback/keycloak
```

```
$ bin/idp-realm-diff --export tests/fixtures/shop-realm-export.json
ok      realm-diff  realm shop: 27 keys and 2 clients declared in git, every one of them matches the realm that is running
```

The file this reads is a full read-back of the sign-in settings, several hundred of them. Only
the twenty-seven git has an opinion about are graded; the rest are the vendor's defaults and are
left alone on purpose, so an upgrade that adds a setting does not turn the check red.

## Now somebody changes it behind our backs

The second file is the same read-back after three clicks: the lock-out switched off, a sign-in
made to last a day, and one extra address added to the shop's own application.

```
$ bin/idp-realm-diff --export tests/fixtures/shop-realm-export-after-a-console-change.json
FAIL    realm-diff  the running realm is not what git says, in 4 places:
        realm.bruteForceProtected: git says true, the realm says false
        realm.accessTokenLifespan: git says 300, the realm says 86400
        realm.clients[clientId=storefront].directAccessGrantsEnabled: git says false, the realm says true
        realm.clients[clientId=storefront].redirectUris: git says ["https://shop.mumchimp.com/api/auth/callback/keycloak"], the realm says ["https://shop.mumchimp.com/api/auth/callback/keycloak", "https://evil.example/callback"]
```

Four lines, each naming the setting, what we said and what is actually there. The last one is the
one that steals accounts: an address nobody owns, added to the list the shop may send a
signed-in customer back to.

## It cannot be green by accident

```
$ bin/idp-realm-diff
BLIND   realm-diff  no realm export was given, so nothing was read back from the server; pass --export FILE (or set IDP_REALM_EXPORT). Absent is not a pass.
```

Nothing read means nothing proved, and nothing proved is never a pass. The same applies inside
the file: if the shop's own address is not supplied, the check refuses rather than treating it as
`anything matches`. A password or an application secret is compared by whether it is there at all,
never by its value, so no secret can reach a build log.

## Prove the whole of it yourself

```
$ python3 -m pytest -q -p no:xdist -o addopts="" tests/test_the_customer_realm_is_code_and_a_console_change_is_caught.py
17 passed
```

## What this does not prove yet

The sign-in service itself is not running. This slice is the rules, the file, the grading and the
proof that a change is caught; the service, its database and the move of the one existing shop
account come next, and the feature stays switched off until then. Nothing here changes what runs
today.
