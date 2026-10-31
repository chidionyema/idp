#!/usr/bin/env python3
"""estate-model-lanes -- what the estate can actually call, at what price, with which credential.

The estate routes every model call through one router, and that router's own ledger knows which
lanes it serves and which it refuses. What it does NOT know -- and what no document in the estate
recorded -- is what each lane COSTS, or which vendor keys exist at all. Two handoffs in a week
disagreed about that ("only 2 vendors work", "4 vendors work"), because nobody had counted.

This reads local files and no network:
  * the router ledger      (~/.estate/router-state/lanes.json)   -- declared, served, refused, and
                                                                     which credential NAME each
                                                                     provider holds;
  * the router catalog     (~/.estate/router-state/catalog.json) -- the model names per alias;
  * the live render config (~/.estate/router-state/config.runtime.yaml) -- the model behind each
                                                                     alias and the api_key env NAME;
  * LiteLLM's own price table (model_prices_and_context_window*.json) -- price per token.

The price table is LiteLLM's, read from the venv, so the prices are the same ones the router
would charge: no scraping a pricing page, no drifting copy.

A credential is reported by NAME and by presence only. A value never enters this file.

Usage:
  estate-model-lanes.py [--ledger P] [--catalog P] [--config P] [--prices P]
                        [--out catalog/model-lanes.json] [--markdown]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any

DEFAULT_STATE = os.path.expanduser("~/.estate/router-state")
PRICE_GLOBS = [
    "~/.cache/estate-tools/litellm-venv/lib/python3.12/site-packages/litellm/model_prices_and_context_window_backup.json",
    "~/.cache/estate-tools/litellm-venv/lib/python3.12/site-packages/litellm/model_prices_and_context_window.json",
    "~/.local/share/uv/tools/*/lib/python3.12/site-packages/litellm/model_prices_and_context_window*.json",
]


def _load(path: str, default: Any = None) -> Any:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def find_price_table(explicit: str = "") -> str:
    if explicit and os.path.exists(explicit):
        return explicit
    for pattern in PRICE_GLOBS:
        for hit in sorted(glob.glob(os.path.expanduser(pattern))):
            if os.path.exists(hit):
                return hit
    return ""


def price_of(prices: dict, model: str) -> dict:
    """LiteLLM's own table, keyed by the bare model name or the provider/name form."""
    if not prices:
        return {}
    bare = model.split("/", 1)[1] if "/" in model else model
    for key in (model, bare, "openrouter/" + bare):
        if key in prices:
            return prices[key]
    for key, value in prices.items():
        if key.endswith("/" + bare):
            return value
    return {}


def per_million(entry: dict, field: str):
    cost = entry.get(field)
    if cost is None:
        return None
    return round(float(cost) * 1000000, 6)


def cost_class(inp, out) -> str:
    if inp is None and out is None:
        return "unknown"
    if (inp or 0.0) == 0.0 and (out or 0.0) == 0.0:
        return "free"
    return "paid"


def alias_models(config: dict) -> dict:
    """alias -> [{model, credential_env_name}] from the live render config."""
    out: dict = {}
    for entry in (config or {}).get("model_list", []) or []:
        name = entry.get("model_name")
        params = entry.get("litellm_params", {}) or {}
        api_key = str(params.get("api_key", ""))
        env = api_key.split("/", 1)[1] if api_key.startswith("os.environ/") else ""
        out.setdefault(name, []).append(
            {"model": params.get("model"), "credential": env}
        )
    return out


def build(
    ledger_path: str, catalog_path: str, config_path: str, prices_path: str
) -> dict:
    ledger = _load(ledger_path, {}) or {}
    catalog = _load(catalog_path, {}) or {}
    config = _load(config_path, {}) or {}
    prices = _load(prices_path, {}) if prices_path else {}

    providers = ledger.get("providers") or {}
    credential_present = {env for envs in providers.values() for env in (envs or [])}
    served = set(ledger.get("served") or [])
    declared = list(ledger.get("declared") or [])
    refused = list(ledger.get("refused_lanes") or ledger.get("dropped") or [])
    by_alias = alias_models(config)
    catalog_models = catalog.get("models") or {}

    lanes = []
    for alias in sorted(set(declared) | served | set(by_alias)):
        entries = by_alias.get(alias) or []
        models = []
        cheapest = None
        priced = 0
        for entry in entries:
            model = entry.get("model") or ""
            info = price_of(prices, model)
            inp = per_million(info, "input_cost_per_token")
            out = per_million(info, "output_cost_per_token")
            if inp is not None or out is not None:
                priced += 1
            if model and model not in [m["model"] for m in models]:
                models.append(
                    {
                        "model": model,
                        "input_usd_per_mtok": inp,
                        "output_usd_per_mtok": out,
                        "cost_class": cost_class(inp, out),
                        "priced": bool(inp is not None or out is not None),
                    }
                )
            if inp is not None and (cheapest is None or inp < cheapest):
                cheapest = inp
        credential = next(
            (e.get("credential") for e in entries if e.get("credential")), ""
        )
        provider = ""
        for entry in entries:
            model = entry.get("model") or ""
            if "/" in model:
                provider = model.split("/", 1)[0]
                break
        lanes.append(
            {
                "alias": alias,
                "provider": provider,
                "credential": credential or None,
                "credential_present": bool(credential)
                and credential in credential_present,
                "declared": alias in declared,
                "served": alias in served,
                "refused": alias in refused,
                "models": models,
                "model_count": len(models) or len(catalog_models.get(alias, [])),
                "priced_models": priced,
                "cheapest_input_usd_per_mtok": cheapest,
                "cost_class": (
                    "unknown"
                    if not priced
                    else (
                        "free"
                        if all(m["cost_class"] == "free" for m in models)
                        else "paid"
                    )
                ),
            }
        )

    summary = {
        "declared_lanes": len(declared),
        "served_lanes": len(served),
        "refused_lanes": len(refused),
        "providers_with_a_credential": sorted(providers),
        "credential_names": sorted(credential_present),
        "lanes_priced": sum(1 for lane in lanes if lane["priced_models"]),
        "lanes_unpriced": sum(1 for lane in lanes if not lane["priced_models"]),
        "free_lanes": sorted(
            lane["alias"] for lane in lanes if lane["cost_class"] == "free"
        ),
        "paid_lanes": sorted(
            lane["alias"] for lane in lanes if lane["cost_class"] == "paid"
        ),
        "unknown_cost_lanes": sorted(
            lane["alias"] for lane in lanes if lane["cost_class"] == "unknown"
        ),
        "price_table": os.path.basename(prices_path) if prices_path else "",
        "price_table_entries": len(prices) if prices else 0,
    }
    return {
        "at": ledger.get("at"),
        "ledger": {"declared": declared, "served": sorted(served), "refused": refused},
        "summary": summary,
        "lanes": lanes,
    }


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "| lane | provider | credential | present | models | priced | in $/Mtok | out $/Mtok | cost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for lane in report["lanes"]:
        models = lane["models"]
        first = models[0] if models else {}
        cred = lane["credential"] or "-"
        present = (
            "yes"
            if lane["credential_present"]
            else ("no" if lane["credential"] else "-")
        )
        inp = first.get("input_usd_per_mtok")
        out = first.get("output_usd_per_mtok")
        lines.append(
            "| {alias} | {provider} | {cred} | {present} | {count} | {priced} | {inp} | {out} | {cost} |".format(
                alias=lane["alias"],
                provider=lane["provider"] or "-",
                cred=cred,
                present=present,
                count=lane["model_count"],
                priced=lane["priced_models"],
                inp="-" if inp is None else "{:.4f}".format(inp),
                out="-" if out is None else "{:.4f}".format(out),
                cost=lane["cost_class"],
            )
        )
    lines.append("")
    lines.append(
        "declared {d}, served {s}, refused {r}; priced {p}, unpriced {u}.".format(
            d=summary["declared_lanes"],
            s=summary["served_lanes"],
            r=summary["refused_lanes"],
            p=summary["lanes_priced"],
            u=summary["lanes_unpriced"],
        )
    )
    lines.append("")
    lines.append(
        "providers holding a credential: "
        + ", ".join(summary["providers_with_a_credential"])
    )
    return "\n".join(lines)


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=os.path.join(DEFAULT_STATE, "lanes.json"))
    parser.add_argument(
        "--catalog", default=os.path.join(DEFAULT_STATE, "catalog.json")
    )
    parser.add_argument(
        "--config", default=os.path.join(DEFAULT_STATE, "config.runtime.yaml")
    )
    parser.add_argument("--prices", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)

    prices_path = find_price_table(args.prices)
    report = build(args.ledger, args.catalog, args.config, prices_path)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("ok    model lanes written: {}".format(args.out))
    if args.markdown:
        print(markdown(report))
    else:
        print(json.dumps(report["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
