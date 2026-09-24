# Onboarding — putting Otto on free GPU capacity

You need this when Otto's free API lanes are not enough: they have all been exhausted for the
day, a vendor has changed its terms, or you want a lane whose model and behaviour nobody but
the estate can change. It gives Otto a fourth failure domain built on Kaggle's free GPU quota —
30 hours a week on a T4 or P100.

## Before you start

Three credentials, and the tool tells you which are missing:

```
bin/idp-kaggle-lane --preflight
```

- **`kaggle-api`** — the founder's Kaggle API token. This is the one genuine console step, and
  it is done once: <https://www.kaggle.com/settings> → API → Create New Token, then Backstage →
  Run the estate bootstrap → scope `kaggle`. Kaggle has no other way to issue one.
- **`cloudflare-tunnel-token`** and **`kaggle-lane-key`** — both minted by
  `bin/idp-bootstrap-cloudflare` from the standing Cloudflare root, with no console step at
  all. Door: Backstage → Run the estate bootstrap → scope `cloudflare`, mode `live`.

You also need the `kaggle` client on the machine that launches (`pip install kaggle`). The
launcher shells out to it rather than reimplementing Kaggle's push protocol.

## Door (from the UI)

Backstage → Otto → **Homes** → *Launch the GPU lane*. The button runs the same command with
the defaults below; the page shows the last push and whether the notebook is serving.

## Launch, and check

```
bin/idp-kaggle-lane                # push and start on a T4, hold 11 of the 12 allowed hours
bin/idp-kaggle-lane --status       # ask Kaggle how that push is doing
bin/idp-kaggle-lane --gpu nvidiaP100 --hours 6
```

## How the Worker finds it

The lifeboat's lane table carries `secret: KAGGLE_LANE_KEY` and `urlVar: KAGGLE_LANE_URL`, not
a hostname. That is deliberate: the estate's DNS zone is one value in
`clusters/*/estate-config.yaml` and no platform file may write it down (LAW 46), so
`bin/idp-otto-homes` passes the address in at deploy time. A lane with either unset is skipped
before any fetch, so an unconfigured lane costs nothing and throws nothing.

## When it does not work

- **`BLIND kaggle-api`** — the token is not in the vault. Run the bootstrap scope above; do not
  paste a token into a session or a file.
- **`FAIL kaggle`** — Kaggle refused the push. The last line of its own error is printed; the
  usual causes are a slug that collides with an existing kernel and a quota that is spent for
  the week.
- **The lane is skipped in the Worker's `tried` list** — the notebook is not running. That is
  the normal state for most of any week: 30 GPU-hours is not 168, and the lane is designed to
  be absent without costing a turn.
