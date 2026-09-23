"""sovereign/consensus/ -- cross-model consensus under a policy invariant
(cp30, spec v1.0 4.2).

Distinct from `sb consensus`, which is cp11's DB-versus-DAG dual read
(sovereign/sidecar/dualread.py). That one asks "do the two stores agree
about a row"; this one asks "do three models agree about a command, and
does policy allow it anyway". Same English word, two unrelated questions,
so they are two modules and two subcommands -- folding them together
would have made `sb consensus --json` mean two things depending on flags.
"""
from __future__ import annotations

from sovereign.consensus.models import normalize_tool_call
from sovereign.consensus.decide import decide

__all__ = ["decide", "normalize_tool_call"]
