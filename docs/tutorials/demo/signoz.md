# Demo: The SigNoz check

Every hour at :47 the estate signs a statement about the SigNoz that is running: it answers, its
dashboards API answers the checker's key, it refuses a caller holding no key, and the front-door
walk to `signoz.<zone>` landed where a person would land. Run it by hand from a laptop, where the
vault is not readable, and the same command lands BLOCKED with the reason instead of pretending:

```
$ bin/idp-prove signoz --out /tmp/v.json
drill   prove  FAIL    login-drill  python python3 has no playwright; pip install playwright && playwright install chromium
ok      prove  l1.signoz.answers                            401
ok      prove  l2.NEGATIVE.no_key_is_refused                401 {}
FAIL    prove  l3.front_door.signoz.reached_host            FAIL    login-drill  python python3 has no playwright
FAIL    prove  prover.blocked                               signoz-prover.key unreadable from the vault (oke-check.yml -f mode=apply runs bin/idp-estate-seed, whose step 4 is bin/idp-signoz-key)
BLOCKED prove  2/4 assertions on docker.io/signoz/signoz@ rev 6 nonce local-ab247ef8917b; UNSIGNED: no verdict-hmac-key (oke-check apply mints it); failed: l3.front_door.signoz.reached_host, prover.blocked
```

Read the two `ok` rows first: the live edge answered a keyless read of `/api/v2/dashboards` with
401, so the door is shut to anyone without the key, measured, not assumed. The `BLOCKED` line is
the point of the design: with no key and no browser the checker says so and signs nothing, where the
old shape would have read a login screen and called it green.

The hourly run on the cluster's identity has the key, the browser and the signing key, and prints:

```
ok      prove  l1.signoz.answers                            401
ok      prove  l2.dashboards.status_200_json                200 dict
ok      prove  l2.dashboards.lists_dashboards               dict {"status":"success","data":{"dashboards":[...],"total":0}}
ok      prove  l2.NEGATIVE.no_key_is_refused                401 {}
ok      prove  l3.front_door.signoz.reached_host            signoz.<zone>/login (200)
FAIL    prove  l3.front_door.signoz.signed_in               /login, 1 password field(s)
BLOCKED prove  L3 cannot pass: SigNoz community has no OIDC/SAML; a second login is expected (crew#718 CP2)
```

That last line stays until SigNoz can take the estate's one login; the check-run on the commit
reads neutral, the row on the estate page reads BLOCKED with that sentence, and nobody has to
remember why. The portal button **verdict-signoz** runs the same workflow on demand.
