"""What /fleet and the face show of the delivery flow: the model, its voids and what is live.

One payload, two readers: the /fleet page and the face draw the same snapshot at any scale, from the
whole estate down to one edge. The model is catalog/intent-flow.json and the voids come from
bin/intent-flow's abyss algorithm, so the picture cannot show a mechanism the repository does not have.

Nothing here is invented. The live part reports what the estate's event spine actually carries; where no
feed is wired it says so with the reason, and the page must draw those packets as simulated, never as live.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[5]


def _root() -> Path:
    return Path(os.environ.get("ESTATE_REPO_ROOT") or _ROOT)


def _tool(root: Path):
    loader = importlib.machinery.SourceFileLoader(
        "intent_flow_tool", str(root / "bin" / "intent-flow")
    )
    spec = importlib.util.spec_from_loader("intent_flow_tool", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def topology_snapshot() -> dict[str, Any]:
    root = _root()
    try:
        tool = _tool(root)
        model = tool.load(root / "catalog" / "intent-flow.json")
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        return {"available": False, "error": "delivery model unreadable: %s" % exc}
    voids = tool.abyss(model, root)
    void_edges = {v["edge"] for v in voids["voids"]}
    states = [dict(id=k, **v) for k, v in model["states"].items()]
    edges = [
        dict(
            source=x["from"],
            target=x["to"],
            event=x.get("event"),
            decider=x["decider"],
            gate=x["gate"],
            evidence=x.get("evidence"),
            void="%s->%s" % (x["from"], x["to"]) in void_edges,
        )
        for x in model["edges"]
    ]
    roles = [dict(id=k, **v) for k, v in model["chain"]["roles"].items()]
    return {
        "available": True,
        "problems": tool.problems(model),
        "states": states,
        "edges": edges,
        "chain": roles,
        "ranks": model["ranks"]["ranks"],
        "rank_order": model["ranks"]["order"],
        "layers": model["dna"]["layers"],
        "abyss": {
            k: voids[k]
            for k in ("verdict", "count", "by_kind", "edges", "edges_with_mechanism")
        },
        "voids": voids["voids"],
        "live": {
            "available": False,
            "error": "no live event feed for this flow: only the flux.reconciled signal flows through the spine "
            "(spine/workflow.py); packets drawn from this snapshot are simulated",
        },
    }
