"""Router catalog: every model the router serves, asked of the providers themselves, written into
every installed harness so each harness's picker is exactly the router.

bin/litellm-local starts this in the background next to the router; it never blocks the router.

  providers -> catalog   lanes.json names each derived provider and its key variables; each
                         provider's own /models endpoint lists what it serves (LiteLLM's static
                         list when the provider has no listing endpoint). A lane pinned to its own
                         endpoint (lanes.json "bases", e.g. a subscription plan) is listed from
                         that endpoint, and a model stays only if it answers a one-token call:
                         Z.ai's plan /models lists glm-5.3-flashx, which the plan refuses (#5697).
  catalog  -> harnesses  one adapter per harness config schema. A harness is added by adding one
                         adapter; a provider needs nothing here at all.

A harness config that does not parse cleanly is left untouched and reported: this never rewrites
a file it cannot read back exactly.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

ROUTER = os.environ.get("ESTATE_ROUTER_URL", "http://127.0.0.1:4000/v1")
KEY_ENV = "LITELLM_API_KEY"  # the one key every harness presents to the router
DISCOVER_TIMEOUT_S = 30


def _http(url: str, key: str, body: dict | None = None) -> dict:
    import urllib.request

    if not url.startswith(("https://", "http://")):
        raise ValueError(f"not an http(s) endpoint: {url}")
    req = urllib.request.Request(  # noqa: S310 - scheme asserted above
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=DISCOVER_TIMEOUT_S) as r:  # noqa: S310
        return json.load(r)


def answers(base: str, key: str, model: str) -> bool:
    """Whether the endpoint serves this model to this key. Only a refusal (4xx) says no: a
    timeout or a 5xx is the endpoint's trouble, not the plan's, and never hides a model."""
    import urllib.error

    try:
        _http(
            base + "/chat/completions",
            key,
            {
                "model": model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "1"}],
            },
        )
    except urllib.error.HTTPError as e:
        return not 400 <= e.code < 500
    except OSError:
        return True
    return True


def listed(base: str, key: str) -> list[str]:
    """The models the endpoint itself lists, kept only if it answers each one."""
    ids = sorted(m["id"] for m in _http(base + "/models", key)["data"])
    return [m for m in ids if answers(base, key, m)]  # one at a time: never a burst


def discover(
    providers: dict[str, list[str]], bases: dict[str, str] | None = None
) -> dict[str, list[str]]:
    """provider -> sorted "<provider>/<model>" ids, from each provider's own listing."""
    bases = bases or {}

    def one(p: str, var: str) -> tuple[str, list[str]]:
        if p in bases:
            ids = listed(bases[p].rstrip("/"), os.environ.get(var, ""))
        else:
            # LAZY (2026-10-29): litellm is imported here, not at the top of the function.
            # A provider that answers its own listing needs no litellm at all, and the
            # unconditional import made the catalogue unusable where litellm is not
            # installed -- measured on the CI runner (idp candidate run 40876656109, job
            # 123457294303): "ModuleNotFoundError: No module named 'litellm'" failed the
            # test that proves a plan lane lists what the plan answers from its own
            # endpoint. The import belongs to the one branch that calls litellm.
            import litellm  # noqa: PLC0415 -- the branch that needs it, and only that one

            ids = litellm.get_valid_models(
                check_provider_endpoint=True,
                custom_llm_provider=p,
                api_key=os.environ.get(var),
            )
        return p, sorted({m if m.startswith(p + "/") else f"{p}/{m}" for m in ids})

    out: dict[str, list[str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(one, p, vs[0]) for p, vs in providers.items() if vs]
        # A plan's listing waits on one probe per model, one after another.
        for f in concurrent.futures.as_completed(futs, timeout=DISCOVER_TIMEOUT_S * 20):
            try:
                p, ids = f.result(timeout=DISCOVER_TIMEOUT_S)
                out[p] = ids
            except Exception as e:  # one provider down never hides the others
                print(f"warn  catalog: {e}", file=sys.stderr)
    return out


def all_models(catalog: dict) -> list[str]:
    ids = list(catalog.get("aliases", []))
    for p in sorted(catalog.get("models", {})):
        ids += catalog["models"][p]
    return list(dict.fromkeys(ids))


def _load_json(path: Path) -> dict | None:
    """The file as JSON, {} when absent, None when it exists but is not plain JSON."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except ValueError:
        return None


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def opencode(catalog: dict, home: Path) -> str:
    path = home / ".config" / "opencode" / "opencode.jsonc"
    if not path.parent.exists():
        return "absent"
    data = _load_json(path)
    if data is None:
        return f"skipped: {path} is not plain JSON"
    prov = data.setdefault("provider", {}).setdefault("litellm", {})
    prov.setdefault("npm", "@ai-sdk/openai-compatible")
    prov.setdefault("name", "Estate Router")
    prov.setdefault("options", {}).update(baseURL=ROUTER, apiKey="{env:%s}" % KEY_ENV)
    prov["models"] = {m: {"name": m} for m in all_models(catalog)}
    _write_json(path, data)
    return f"{len(prov['models'])} models"


def working_window() -> int:
    """The router's per-call input ceiling: the one number a harness must compact against.

    Read from request_ceiling so the two cannot drift. A harness told nothing assumes its own
    default (pi: 128000), compacts against that, and meets the router's refusal at a different
    size than it planned for."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import request_ceiling  # noqa: PLC0415 -- sibling module; importable without litellm

    return request_ceiling.MAX_INPUT_TOKENS


def _tokens(size: str) -> int:
    """`pi --list-models` sizes: "200K", "204.8K", "1M"."""
    scale = {"K": 1_000, "M": 1_000_000}.get(size[-1:].upper(), 1)
    return int(float(size.rstrip("KMkm")) * scale)


def parse_list_models(text: str) -> dict[str, dict[str, int]]:
    """provider -> model id -> context window, from `pi --list-models`' table."""
    out: dict[str, dict[str, int]] = {}
    for line in text.splitlines()[1:]:
        cols = line.split()
        if len(cols) >= 3:
            try:
                out.setdefault(cols[0], {})[cols[1]] = _tokens(cols[2])
            except ValueError:
                continue
    return out


def pi_bin() -> str | None:
    """pi's executable. launchd starts the router with PATH=/usr/bin:/bin:/usr/sbin:/sbin, and
    pi lives under nvm, so PATH alone never finds it there."""
    import glob
    import shutil

    found = os.environ.get("ESTATE_PI_BIN") or shutil.which("pi")
    if found:
        return found
    nvm = sorted(glob.glob(str(Path.home() / ".nvm/versions/node/*/bin/pi")))
    return nvm[-1] if nvm else None


def pi_listed() -> dict[str, dict[str, int]] | None:
    """Every model pi can call right now, with the window pi compacts against. None when pi is
    not found or does not answer: the overrides it feeds are then left as they were."""
    import subprocess

    exe = pi_bin()
    if exe is None:
        return None
    # pi is `#!/usr/bin/env node`: its own directory holds the node it was installed with.
    env = {
        **os.environ,
        "PATH": str(Path(exe).parent) + os.pathsep + os.environ.get("PATH", ""),
    }
    try:
        r = subprocess.run(
            [exe, "--list-models"],
            capture_output=True,
            text=True,
            timeout=DISCOVER_TIMEOUT_S,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_list_models(r.stdout) if r.returncode == 0 else None


def pi(catalog: dict, home: Path) -> str:
    path = home / ".pi" / "agent" / "models.json"
    if not path.parent.exists():
        return "absent"
    data = _load_json(path)
    if data is None:
        return f"skipped: {path} is not plain JSON"
    # Without contextWindow pi resolves every model to 128000 (provider-composer.js), measured
    # 2026-10-20 with `pi --list-models`. It then compacts against 128000 while the router allows
    # 200000, or, worse, against nothing it can see when a single turn is larger than either.
    window = working_window()
    models = [{"id": m, "contextWindow": window} for m in all_models(catalog)]
    providers = data.setdefault("providers", {})
    providers["estate"] = {
        "baseUrl": ROUTER,
        "api": "openai-completions",
        "apiKey": "$" + KEY_ENV,
        "models": models,
    }
    # pi also calls providers directly with its own keys (auth.json), never touching the router.
    # Those built-in models declare their native windows (deepseek-flash, deepseek-v4-pro and
    # MiniMax-M3: 1M), so pi compacted against 1M: 7,912 of 7,936 over-ceiling pi calls went
    # this way (docs/diagnoses, idp#6675). Each model above the ceiling is capped to it; one at
    # or below keeps its own window, which is the real limit there.
    listed = pi_listed()
    if listed is None:
        _write_json(path, data)
        return f"{len(models)} models, direct not checked (pi not found)"
    capped = 0
    for provider, windows in listed.items():
        if provider == "estate":
            continue
        for model_id, native in windows.items():
            # pi lists a window after applying the overrides, so a model capped by an earlier
            # run shows the ceiling, not its native size: it stays capped and is counted.
            existing = (
                providers.get(provider, {}).get("modelOverrides", {}).get(model_id, {})
            )
            if native > window or existing.get("contextWindow") == window:
                overrides = providers.setdefault(provider, {}).setdefault(
                    "modelOverrides", {}
                )
                overrides.setdefault(model_id, {})["contextWindow"] = window
                capped += 1
    _write_json(path, data)
    return f"{len(models)} models, {capped} direct capped"


ADAPTERS = {"opencode": opencode, "pi": pi}


def build(lanes: dict, discovered: dict[str, list[str]]) -> dict:
    return {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "router": ROUTER,
        "aliases": sorted(m for m in lanes.get("served", []) if "*" not in m),
        "models": discovered,
    }


def sync(catalog: dict, home: Path) -> dict[str, str]:
    result = {}
    for name, adapt in ADAPTERS.items():
        try:
            result[name] = adapt(catalog, home)
        except Exception as e:
            result[name] = f"error: {e}"
    return result


def main(lanes_path: str) -> int:
    lanes = json.loads(Path(lanes_path).read_text())
    catalog = build(lanes, discover(lanes.get("providers", {}), lanes.get("bases", {})))
    catalog["harnesses"] = sync(catalog, Path.home())
    _write_json(Path(lanes_path).with_name("catalog.json"), catalog)
    n = sum(len(v) for v in catalog["models"].values())
    print(
        f"catalog {n} models from {len(catalog['models'])} providers; harnesses {catalog['harnesses']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
