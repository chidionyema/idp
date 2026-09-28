import yaml
from pathlib import Path
from functools import lru_cache

SCHEMAS = Path(__file__).resolve().parent / "schemas"


@lru_cache(maxsize=1)
def _cfg():
    p = SCHEMAS / "shapes.yaml"
    data = yaml.safe_load(p.read_text())["shape_system"]
    return {
        "declared": {
            (d["sub"], d["sup"]) for d in data.get("declared_subsumptions", [])
        },
        "atoms": {a["id"] for a in data.get("atoms", [])},
    }


def parse(s: str):
    s = s.strip()
    if s == "any":
        return ("atom", "any")
    if s.endswith("?"):
        return ("optional", parse(s[:-1]))
    if s.startswith("[") and s.endswith("]"):
        return ("list", parse(s[1:-1]))
    if "|" in s:
        return ("union", tuple(parse(p.strip()) for p in s.split("|")))
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1]
        fields, buf, depth, parts = {}, "", 0, []
        for ch in inner:
            if ch in "{[":
                depth += 1
            elif ch in "}]":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            parts.append(buf)
        for p in parts:
            if ":" not in p:
                continue
            k, v = p.split(":", 1)
            fields[k.strip()] = parse(v.strip())
        return ("record", fields)
    return ("atom", s)


def to_str(node):
    k, v = node
    if k == "atom":
        return v
    if k == "optional":
        return to_str(v) + "?"
    if k == "list":
        return f"[{to_str(v)}]"
    if k == "union":
        return "|".join(to_str(m) for m in v)
    if k == "record":
        return "{" + ", ".join(f"{a}: {to_str(b)}" for a, b in v.items()) + "}"
    return "any"


def subsumes(sup: str, sub: str, _depth: int = 0) -> bool:
    """True if `sup` accepts everything `sub` produces. Total, decidable, no fuzz."""
    if _depth > 32:
        return False
    sup, sub = sup.strip(), sub.strip()
    if sup == "any" or sup == sub:
        return True
    cfg = _cfg()
    if (sub, sup) in cfg["declared"] or (sup, sub) in cfg["declared"]:
        return True
    sp, ssub = parse(sup), parse(sub)
    if sp[0] == "record" and ssub[0] == "record":
        for f, st in sp[1].items():
            if f not in ssub[1]:
                return False
            if not subsumes(to_str(st), to_str(ssub[1][f]), _depth + 1):
                return False
        return True
    if sp[0] == "union":
        return any(subsumes(to_str(m), sub, _depth + 1) for m in sp[1])
    if sp[0] == "optional":
        return subsumes(to_str(sp[1]), sub, _depth + 1)
    if ssub[0] == "optional":
        return subsumes(sup, to_str(ssub[1]), _depth + 1)
    return False
