"""python -m factory.surfaces._scaffold <id> "<Name>" <transport>"""

import sys
from pathlib import Path
from datetime import date

TEMPLATE_PY = """from ..base import Surface
from ... import llm, ledger
import os, json, hashlib, time

class {Class}Surface(Surface):
    id = "{id}"

    def __init__(self):
        # TODO: read config from env
        pass

    def intake(self):
        # TODO: read from {transport} inbox; decompose via llm.decompose
        return None

    def deliver(self, order, message):
        # TODO: send via {transport}; return {{"delivered": bool, "reason": ...}}
        return {{"delivered": False, "reason": "NOT_IMPLEMENTED"}}

    def receipt(self):
        return None
"""

TEMPLATE_YAML = """terminals:
  - terminal:
      id: intake.{id}
      name: "Intake — {name}"
      input:  {{ shape: human.expression }}
      output: {{ shape: need }}
      grade:
        metric: accuracy
        polarity: maximize
        scale: [0,1]
        gate: {{ terminal: grammar.admission_test, sandbox: subprocess }}
      state: current
      since: "{today}"
      annotations:
        class: surface
        mode: frontier-call
        scope: {{ resources: [{transport}], secrets: {{}}, tenant_isolated: false }}
        surface: {id}
  - terminal:
      id: deliver.{id}
      name: "Deliver — {name}"
      input:  {{ shape: agent.output }}
      output: {{ shape: human.receives }}
      grade:
        metric: delivered
        polarity: maximize
        scale: [0,1]
        gate: {{ terminal: delivery_delivered, sandbox: subprocess }}
      state: current
      since: "{today}"
      annotations:
        class: surface
        mode: function
        scope: {{ resources: [{transport}], secrets: {{}}, tenant_isolated: false }}
        surface: {id}
  - terminal:
      id: receipt.{id}
      name: "Receipt — {name}"
      input:  {{ shape: human.receipt }}
      output: {{ shape: grade.signal }}
      grade:
        metric: engagement
        polarity: maximize
        scale: [0,1]
        gate: {{ terminal: delivery_delivered, sandbox: subprocess }}
      state: current
      since: "{today}"
      annotations:
        class: surface
        mode: function
        scope: {{ resources: [{transport}], secrets: {{}}, tenant_isolated: false }}
        surface: {id}
"""


def main():
    if len(sys.argv) < 4:
        print("usage: python -m factory.surfaces._scaffold <id> '<Name>' <transport>")
        print(
            "transports: http-webhook | http-poll | websocket | mqtt | bluetooth | serial"
        )
        sys.exit(1)
    sid, name, transport = sys.argv[1], sys.argv[2], sys.argv[3]
    cls = "".join(p.capitalize() for p in sid.split("_"))
    base = Path(__file__).resolve().parent / sid
    base.mkdir(parents=True, exist_ok=True)
    (base / "__init__.py").write_text("")
    (base / "surface.py").write_text(
        TEMPLATE_PY.format(id=sid, Class=cls, transport=transport)
    )
    (Path(__file__).resolve().parent.parent.parent / "surfaces").mkdir(exist_ok=True)
    (
        Path(__file__).resolve().parent.parent.parent / "surfaces" / f"{sid}.yaml"
    ).write_text(
        TEMPLATE_YAML.format(
            id=sid, name=name, transport=transport, today=date.today().isoformat()
        )
    )
    print(f"scaffolded {sid} over {transport}")
    print(f"  edit: factory/surfaces/{sid}/surface.py")
    print(
        f"  add to registry.py: if os.environ.get('{sid.upper()}_TOKEN'): from .{sid}.surface import {cls}Surface; out.append({cls}Surface())"
    )
    print(f"  run:  python -m factory.main collect")


if __name__ == "__main__":
    main()
