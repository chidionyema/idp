"""Independent, epoch-fenced instruction settlement.

The worker and supervisor are not settlement authorities. The probe must be
supplied by the trusted runtime and observe the actual effect out of band.
This implementation is process-local; durable custody belongs to the runtime.
"""

from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True, slots=True)
class ProbeReceipt:
    instruction_id: str
    epoch: int
    commit_sha: str
    ok: bool


class Probe:
    """Independent verifier of the admitted predicate and deployed revision."""

    def verify(self, iid):
        raise NotImplementedError


class Custody:
    TERMINAL = frozenset(("SETTLED", "CANCELLED"))

    def __init__(self, prober, *, authorize_cancel=None):
        self.prober = prober
        self.authorize_cancel = authorize_cancel
        self.instr = {}
        self._settled_keys = set()
        self._lock = RLock()

    def admit(self, iid, predicate, retries=12):
        if not iid or not predicate or retries < 0:
            raise ValueError("invalid instruction")
        with self._lock:
            if iid in self.instr:
                raise ValueError("instruction already admitted")
            self.instr[iid] = dict(
                state="ADMITTED",
                epoch=0,
                retries=retries,
                predicate=predicate,
                commit_sha=None,
                expected_commit_sha=None,
            )

    def lease(self, iid, *, expected_commit_sha=None):
        with self._lock:
            r = self.instr[iid]
            if r["state"] in self.TERMINAL:
                raise ValueError("terminal instruction cannot be leased")
            if expected_commit_sha is not None and (
                not isinstance(expected_commit_sha, str)
                or not expected_commit_sha.strip()
            ):
                raise ValueError("invalid expected revision")
            r["epoch"] += 1
            r["state"] = "LEASED"
            r["expected_commit_sha"] = expected_commit_sha
            return r["epoch"]

    def on_worker_exit(self, iid, verdict, *, epoch=None):
        with self._lock:
            r = self.instr[iid]
            if epoch is not None and epoch != r["epoch"]:
                return r["state"]
            if r["state"] in ("LEASED", "ADMITTED"):
                r["state"] = "DELIVERED"
            return r["state"]

    def on_supervisor_verdict(self, iid, approved):
        with self._lock:
            return self.instr[iid]["state"]

    def record_yield(self, iid, agent_claim=None):
        with self._lock:
            r = self.instr[iid]
            if r["state"] in self.TERMINAL or r["epoch"] == 0:
                return r["state"]
            epoch = r["epoch"]
        # Never hold the custody lock during external observation.
        try:
            receipt = self.prober.verify(iid)
        except Exception:
            with self._lock:
                return self.instr[iid]["state"]
        with self._lock:
            r = self.instr[iid]
            if r["state"] in self.TERMINAL or r["epoch"] != epoch:
                return r["state"]
            if (
                not isinstance(receipt, ProbeReceipt)
                or receipt.ok is not True
                or receipt.instruction_id != iid
                or type(receipt.epoch) is not int
                or receipt.epoch != epoch
                or not isinstance(receipt.commit_sha, str)
                or not receipt.commit_sha.strip()
                or r["expected_commit_sha"] is None
                or receipt.commit_sha != r["expected_commit_sha"]
            ):
                return r["state"]
            key = (iid, receipt.commit_sha)
            if key not in self._settled_keys:
                self._settled_keys.add(key)
                r["state"] = "SETTLED"
                r["commit_sha"] = receipt.commit_sha
            return r["state"]

    def on_capability_exhausted(self, iid):
        with self._lock:
            r = self.instr[iid]
            if r["state"] not in self.TERMINAL:
                r["state"] = "RECOVERING"
            return r["state"]

    def cancel(self, iid, principal_sig):
        with self._lock:
            r = self.instr[iid]
            if r["state"] in self.TERMINAL:
                return r["state"]
            if (
                self.authorize_cancel is not None
                and self.authorize_cancel(iid, r["epoch"], principal_sig) is True
            ):
                r["state"] = "CANCELLED"
            return r["state"]


class MockProbe(Probe):
    """Test double only; never use worker-controlled data in production."""

    def __init__(self, world):
        self.world = world

    def verify(self, iid):
        e = self.world.get(iid)
        if not e:
            return None
        return ProbeReceipt(iid, e["epoch"], e["sha"], e["effect_present"])
