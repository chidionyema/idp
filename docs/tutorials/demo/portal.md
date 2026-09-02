# Watch the catalogue overlay

The pitch in one line: open the portal locally and the catalogue lists every kind, in
plain English, with Backstage's own pagination — not a second feed.

## Run it

From `backstage/` (Node 22, shop already owns port 3000):

```
$ yarn start
[webpack-dev-server] Loopback: http://localhost:3100/, http://127.0.0.1:3100/
```

```
$ curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3100/catalog
200
```

## What to show

1. Open http://localhost:3100/catalog — the shop stays on http://localhost:3000/.
2. The first five doors read Home, Catalogue, Health, Docs, You. Operator doors sit under More.
3. The table is every kind (systems, groups, components), cursor-paged, not "owned components".

## What to expect

Unauthenticated local still hits the front-door sign-in page ("Your sign-in did not
reach the portal") because production auth is the Oracle login on the live host.
Live `https://catalogue.mumchimp.com/catalog` stays old until this branch merges and rolls.
