"""The fallback chain terminates at the local floor, never at a paid pool (idp#3525 CP3,
ROUTE-06).

"The fallback chain SHALL terminate at the always-on local tiny model answering openly marked
DEGRADED -- never at a paid pool that can be systemically down in the same event. Never silently
fail." ACCEPT: kill all external lanes -> local model answers with DEGRADED marker; no request
drops.

`run_chain()` tries every external lane in order and swallows each one's exception -- a paid
pool going down is not this function's problem, it just means the chain moves on -- but the
local lane is not one more item in that list: it is a required, separate argument, called only
after every external lane has already failed, and it is the one call this function does not
wrap in try/except. A local lane that itself raises is a defect in the local lane (it is
supposed to be the floor that cannot go down), not something this function papers over; papering
over it would be exactly the "silently fail" the rule forbids.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChainResult:
    degraded: bool
    lane: str
    value: Any


def run_chain(
    external_lanes: list[tuple[str, Callable[[], Any]]],
    local_lane: tuple[str, Callable[[], Any]],
) -> ChainResult:
    for name, call in external_lanes:
        try:
            return ChainResult(degraded=False, lane=name, value=call())
        except Exception:
            logger.warning("fallback_chain: external lane %r failed, trying next", name)
    local_name, local_call = local_lane
    return ChainResult(degraded=True, lane=local_name, value=local_call())
