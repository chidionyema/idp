# Onboarding: money

## What it is for

The application must never touch money. Today the store's own code builds payment sessions
and reads payment webhooks, which means a card, a secret and a signature all live inside
business logic. This layer takes all three out. One service holds the payment provider's
keys, takes the payment, writes it to its own ledger, and then tells the rest of the estate
what happened with a single plain message:

```
{"event": "estate.commerce.order_paid", "user_id": "usr_998",
 "item_sku": "100_ai_credits", "amount_paid": 2000, "currency": "USD"}
```

Nothing downstream knows which provider was used, or that a card exists. Swapping the
provider becomes a change in one service instead of a change in every product.

It covers both of the things a customer can buy: a subscription that renews, and a one-off
pack of credits that sits in a wallet and is drawn down. That is why the layer is Lago and
not a shop engine — a shop engine would have needed a subscriptions plugin written by us,
which is the kind of half-stitched piece a buyer takes apart in one sitting.

## What it costs

Nothing at all today. The feature register defaults it to `off` and all three delivery rows
are suspended, so `bin/idp-features plan` counts zero CPU, zero memory and zero storage for
it. Switched on, the eleven standing pods ask for **1.035 CPU and 3.41 Gi**, plus 5 Gi of disk
for the ledger database and its cache, and one more 100m / 512Mi pod that runs the database
migration once at install and exits. Those numbers are not a reading of a values file: they
come from rendering the chart the way Flux will and adding up the pods, which is the only
place a size exists. `tests/test_crew623_money_never_enters_the_application.py` renders it the
same way on every run, so the figure above cannot drift from the manifests without a red test:

| what | CPU | memory |
|---|---|---|
| Lago, eight Deployments | 0.775 | 2.75 Gi |
| Ledger database | 0.100 | 0.25 Gi |
| Ledger cache | 0.050 | 0.13 Gi |
| Event bus, with its metrics exporter | 0.110 | 0.28 Gi |
| **standing total** | **1.035** | **3.41 Gi** |

Every one of those is written into the manifests in this repository rather than left to the
chart, because the chart's own defaults ask for 6.80 CPU — more than the entire node — and a
default is not something any guard here can read.

Adding roughly one core and three gigabytes to what already runs will not fit the current
6 OCPU / 24 Gi node beside everything else. Turning this on is therefore a node decision as
well as a switch, and the planner will say so before anything is applied.

## Where it lives

- `platform/commerce/data` — the ledger database and its cache, and the vault entries they read.
- `platform/commerce/app` — the money service itself.
- `platform/event-bus` — the bus that carries the paid message, and the written contract for it.
- `clusters/oke/commerce.yaml` — the three delivery rows, all suspended.
- `platform/features/features.yaml` — the register entry, defaulting to `off`.

Its secrets are born in `platform/oci/commerce.tf` and are minted by the pipeline, not typed
by a person. One item is still outstanding and is recorded honestly in the trust register:
the payment provider's own key, which is the single value a human has to supply once.

## How to turn it on

It is deliberately not one switch. Four separate things hold it off — the register default,
the suspended rows, the absent edge label, and every ingress disabled — so that no single
mistake can put a payment path on the internet. Turning it on is a pull request that changes
all four together, and that pull request is the moment the founder decides, not the moment an
agent decides.

## How to stop it

Suspend the three rows again in `clusters/oke/commerce.yaml`. The ledger database keeps its
disk, so nothing that was already taken is lost, and the products fall back to whatever they
did before. To remove it entirely, delete the three rows and the three directories; the
namespace is annotated so Flux will not prune it out from under a running database.
