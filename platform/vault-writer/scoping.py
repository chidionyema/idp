"""The vault writer's allow-list: which entries a customer may write, and which they may not.

docs/specs/key-ingest-door-part4.md, part B.

docs/specs/key-ingest-door-part4.md, part B. The rule this enforces is decision 0021: an
operator identity gets no wider reach here than customer zero does. So the writer will accept a
write to an entry whose register Owner is `Customer`, and refuse one whose Owner is `Operator` --
even though the process could physically reach it, because the OCI statement is scoped by name
list (part C).

Why this file exists at all, and why it is pure: the same rule is enforced twice, once here
before the write leaves the pod and once by the OCI policy's `where target.secret.name in (...)`.
A module with no cluster, no network and no vault client is the only way to prove the first half
in a test.

Parsing the register. It is a markdown table whose real shape (measured 2026-09-10) differs from
any fixture: the `Vault entry` cell holds BACKTICK-QUOTED names, often SEVERAL per row, and some
cells carry a parenthetical suffix after the backticks:

    | `DEEPSEEK_API_KEY` `MINIMAX_API_KEY` ... | ... | ... | Customer | ... |
    | `litellm-upstream` (vendor keys) | ... | ... | Customer | ... |

So a parser that took the cell as one name would produce `litellm-upstream` (vendor keys) -- a
secret that does not exist -- and a parser that took only the first backtick would silently drop
every key after the first. Both are the kind of quiet wrongness this estate keeps paying for.
"""

from __future__ import annotations

import pathlib
import re

# A name inside backticks. The register uses these for every vault entry and every key inside
# one, so one regex covers both the multi-name cells and the single-name fixture shape.
_BACKTICKED = re.compile(r"`([^`]+)`")

# The column that decides. Matched by HEADER NAME, not a fixed index: the real register has
# seven columns and the test fixture has three, and an index would be right for exactly one.
_OWNER_COLUMN = "Owner"

# The entry column has carried two header names: the real register says `Vault entry`, the
# shape a fixture uses is `Entry`. Both are accepted rather than one, because a name-exact
# match on a header that has already been renamed once is the kind that fails silently and
# returns an empty list -- the door would then refuse every legitimate write instead of the
# operator ones, which is a worse failure than the one it guards against.
_ENTRY_COLUMNS = ("Vault entry", "Entry")

# Decision 0021. The only Owner value that may be written through the door.
_CUSTOMER = "Customer"


def _rows(register_path: str | pathlib.Path) -> list[list[str]]:
    """Every data row of the register's markdown table, as lists of stripped cells.

    Header row is excluded by locating it, and the `|---|` separator by its dashes, so a table
    that grows a column keeps working.
    """
    text = pathlib.Path(register_path).read_text()
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        # the |---|---| separator
        if cells and all(set(c) <= set("-: ") and "-" in c for c in cells):
            continue
        rows.append(cells)
    return rows


def _header_index(rows: list[list[str]], columns: str | tuple[str, ...]) -> int | None:
    """Index of a named column, or None when the table does not carry it.

    `columns` may be one name or several accepted aliases; the first match in header order
    wins.
    """
    names = (columns,) if isinstance(columns, str) else columns
    for row in rows:
        for i, cell in enumerate(row):
            if cell in names:
                return i
    return None


def _names_in_cell(cell: str) -> list[str]:
    """Every vault-entry name in one `Vault entry` cell.

    Backticked names when the cell has them (the real register), the whole trimmed cell when it
    does not (the fixture shape, and any hand-written row without backticks). A parenthetical or
    trailing comment after the backticks is dropped, because it is a note about the entry and
    not part of its name.
    """
    found = _BACKTICKED.findall(cell)
    if found:
        return [n.strip() for n in found if n.strip()]
    bare = cell.strip()
    return [bare] if bare else []


def customer_owned_entries(register_path: str | pathlib.Path) -> list[str]:
    """Every vault entry whose register Owner is `Customer`, sorted and de-duplicated.

    This is the list the OCI grant is generated from (part C), so it has to be exactly the names
    the register carries -- no backticks, no parentheticals, no duplicates when two rows mention
    the same key.
    """
    rows = _rows(register_path)
    owner_i = _header_index(rows, _OWNER_COLUMN)
    entry_i = _header_index(rows, _ENTRY_COLUMNS)
    if owner_i is None or entry_i is None:
        return []
    out: set[str] = set()
    for row in rows:
        if owner_i >= len(row) or entry_i >= len(row):
            continue
        if row[owner_i] != _CUSTOMER:
            continue
        out.update(_names_in_cell(row[entry_i]))
    return sorted(out)


def entry_is_customer_owned(register_path: str | pathlib.Path, entry: str) -> bool:
    """True only when `entry` is a Customer-owned name in the register.

    An unknown entry is False, and so is one that appears only on an Operator row -- the caller
    refuses both, which is what keeps the door from being a general write primitive into the
    vault (part 2 of the spec).
    """
    return entry in set(customer_owned_entries(register_path))
