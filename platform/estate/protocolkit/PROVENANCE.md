# PROVENANCE - the founder's protocol kit, vendored

The kit in this directory is the **founder-supplied artifact**, not a rewrite of it.
It was handed over as a directory on the founder's machine (`/tmp/protocolkit`, outside
every git repository, so it was one reboot from being lost) and was never committed
anywhere in the estate. It is vendored here so it can never be lost again, and so the
repository's own gates grade it.

## What changed in the vendored copy, and what did not

**The executable bodies: nothing but two comment lines per Python file.** Each `.py`
file here begins with:

```python
# ruff: noqa
# fmt: off
```

Those two lines are the file-level opt-outs ruff provides for vendored code. Without
them the estate's own Python standard (`bin/idp-python-strict`, rows `ruff check
--select E9,F,B,S` and `ruff format --check`) would fail the founder's kit for two
reasons that are not defects:

* `F401`/`F405` - the kit's public API is defined by deliberate re-export and
  star-imports in `protocolkit/__init__.py` and in its own test file;
* `ruff format` - the kit is not written in ruff's formatting.

Rewriting the kit to satisfy those checks would have edited the founder's code. A
comment changes nothing: every line of executable code is byte-identical to the
original, and the repository's test wrapper
(`tests/estate/test_protocolkit_kit.py`) runs the founder's own 23-test suite
against this vendored copy.

The proof that the bodies are identical is mechanical, and repeatable:

```bash
cd platform/estate/protocolkit
for f in protocolkit/*.py test_protocolkit.py; do
  diff <(tail -n +3 "$f") "/tmp/protocolkit/$f" || echo "DIFFERS: $f"
done
```

It prints nothing.

**`SPEC.md`: eight prose lines transliterated to ASCII.** The estate's own pre-push
gate refuses non-ASCII bytes in the ADDED lines of a diff
(`.githooks/pre-push`, Layer 1c), and the founder's specification uses `->` arrows,
`<=` and `>=` written as Unicode. The mapping applied, and nothing else:

| original | vendored | occurrences |
|---|---|---|
| U+2192 RIGHTWARDS ARROW | `->` | 15 |
| U+2264 LESS-THAN OR EQUAL TO | `<=` | 2 |
| U+2265 GREATER-THAN OR EQUAL TO | `>=` | 3 |

No word, no number, no table cell and no stage name changed: `SPEC.md` differs from
the original only in those 20 characters, and the full diff is 8 changed lines. The
executable kit never reads `SPEC.md`, so this cannot change behaviour.

## Hashes

`original` is the sha256 of the founder's file. `vendored` is the sha256 of the file
as committed here.

| file | original | vendored |
|---|---|---|
| `SPEC.md` | `d7b6f443c6f1ba10cfd01b9fd923394bd7c6c2ba0cd670125ae80b79e76e5721` | `94164ee6889bf67dfe345acd3eb61f4f77039b340d7fee275c0f9ad9385e3cac` |
| `protocolkit/__init__.py` | `cc64d1f8e10ee53fbb00d63100303874901da316565f7b0f2f40a335b3de0269` | `238247a265811086301a16836f3f7244895b8b61a7089ab7369736a5b6beffd0` |
| `protocolkit/gates.py` | `fa116e66512c7a9f8883690de4f9bb8f6209b42500e83028de1f8e6e245b2ddd` | `88b2c62bce072a7b84d1a4d31d3e828dd22e42a37150106df02f201c93b22f63` |
| `protocolkit/genesis.py` | `9105d3acd0bed7b15072ef61d0a4d7968c4c89558299e2b5c6c800f7b7fe2807` | `526c59c3e7d26c77b1c5a611bda79a20df1ef57f1e7fe0095f2005aa0a64355f` |
| `protocolkit/model.py` | `ae2012924e7309a537e7b931c9aa34e3ca2b486c180b706e3ae1df4db59cc84f` | `5674dab1fcae0491943f5be0e76fa20bae6d5e88156605c35d14400c2e7db506` |
| `protocolkit/registry.py` | `077ee5dccf6fd314a3a5034c511608fe5ed260457a778fe89f3f6220e4cfe98a` | `b95e5c03a2e3e34f4ac9f2af87a5c780315b3fe265df1f8cb3b08443a180c86b` |
| `protocolkit/runtime.py` | `99583318b9cb1a9a4795e8409f936d15c299c97973ca8ff1ddd61b45dbd66623` | `2904456d2b61f29bf7a9bff2eb0ac6b958235967dc9588370481229f6c10e7ff` |
| `test_protocolkit.py` | `132dad566f56cb110817a61e1b8c6f6a033bd2dcfdd87f0fee34d05fdbbce560` | `e8604f159d77b4e0bff9a5d228c7e85d539139136a605511c2b2987bf8fbaa39` |

## How the kit is loaded

**Never by `import protocolkit`.** The kit's own directory name shadows the package:
`/tmp/protocolkit` is a directory without `__init__.py`, so it is a *namespace package*
and wins the import over any real package of the same name. Importing it plainly
produced:

```
ImportError: cannot import name 'FounderPrompt' from 'protocolkit' (unknown location)
```

So every consumer loads it **by explicit file path**
(`importlib.util.spec_from_file_location` with `submodule_search_locations`,
registered in `sys.modules` before execution) - see
`platform/estate/governance/plan_links.py` and
`tests/estate/test_protocolkit_kit.py`.

## What the kit is

See `SPEC.md`. In one paragraph: a founder prompt binds to **exactly one** protocol
(`grounded_inquiry`, `execution`, `deep_synthesis`); a protocol is a closed, ordered
pipeline of stages that exchange typed artifacts, never prose; and output reaches the
user only through `Run.egress()`, after every gate of the run has passed. The
`execution` protocol's stages are `invocation -> instruction -> state_assessment ->
action_plan:dry_run -> commit -> response`, gated E1-E5.

The estate uses the kit for one thing today: **every plan must name the instruction it
came from and the founder prompt that started it, and every founder prompt must bind
to exactly one protocol.** That is `platform/estate/governance/plan_links.py` and
`bin/estate-plan-links`.
