"""The vault entry the estate-memory door reads must be one vault-seed delivers to the laptop.

runtimes.json named dev/MCP_GATEWAY_KEY and nothing ever wrote it, so every brief, recall and
remember from the Mac was refused "no MCP_GATEWAY_KEY" (2026-10-14). This reads the door's vault
entry and checks that the laptop delivery in vault-seed both writes it and stages the new file.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOOR = json.loads((ROOT / "platform/estate/memory/runtimes.json").read_text())["door"]
SEED = (ROOT / ".github/workflows/vault-seed.yml").read_text()


def _laptop_block() -> str:
    start = SEED.index('[ "$ENTRY" = laptop ]')
    return SEED[start : SEED.index('[ "$ENTRY" = all ] ||', start)]


def test_vault_seed_delivers_the_entry_the_memory_door_reads():
    env, name, key = DOOR["vault_entry"]
    block = _laptop_block()
    assert f'secret-add" {env} {name} {key}' in block, f"nothing writes {env}/{name}"
    staged = next(line for line in block.splitlines() if " add secrets/" in line)
    assert f"secrets/{env}/{name}.yaml" in staged, (
        f"{env}/{name}.yaml is written but never staged"
    )
