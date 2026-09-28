"""The estate's drifts, carried back to the pull request that caused them.

Spec: docs/specs/2026-09-13-gitops-sync-engine.md

THE FAILURE THIS EXISTS TO END. On 2026-09-13 the estate had six Kustomizations
that were not Ready and a HelmRelease whose health check had been timing out for
twenty minutes. Nothing said so. Six is not a small number and twenty minutes is
not a short time, and the only reason anyone knows either is that an agent ran
`kubectl get kustomizations` by hand and read it.

Flux reported all of it the whole time. What Flux cannot do is name the pull
request. It says:

    health check failed after 20m0.036186674s: timeout waiting for: [HelmRelease/temporal]

which names the symptom and the object and stops there. So the person who caused
it -- who changed a value an hour ago and has moved on -- is the one person not
told, and the one person who could fix it in a minute. That is the same class as
the langfuse reservation that stayed at 1000m for five days while the file
claimed 500m: the estate knows its state and does not know how it got here.

WHY A SENSOR AND NOT A SCRIPT. `holmes_watch.py` next door already does exactly
this shape and is the standing proof it works: a Dagster sensor polls a live
source, fingerprints the situation so one outage is one investigation, isolates a
cause, and delivers through `apprise.notify`. This is that shape pointed at Flux
instead of Alertmanager. It adds no component -- Dagster already schedules it,
GitHub already receives the comment, Flux already knows the drift -- and a shell
script on a launchd timer reading `kubectl get kustomizations` would be a second
scheduler (LAW 43; `bin/idp-one-scheduler` names exactly this), a second delivery
path, and a thing with no memory of what it had already said.

ATTRIBUTION BEFORE REPAIR (LAW 29). This module may only state that a pull request
caused a drift when it can point at the file and the commit. When it cannot, it
says so, and it still reports the drift: a finding deleted because the finder
could not file it is worse than a finding filed as unknown.

NOTHING HERE ACTS. This reports. Repairing a bad rollout is `execute_change` and
its graders (MUM-288, decision 0028), where a proposal is made, graded and
expires -- not a watcher with a revert button.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

import requests

# The sender's name, first thing in every message it sends. Several programs share
# the founder's one chat and a message that does not say who is speaking is a
# defect.
SENDER = "GITOPS"

APPRISE_URL = os.environ.get(
    "ESTATE_APPRISE_URL", "http://apprise.notify.svc.cluster.local:8000"
)
NOTIFY_CHANNEL = os.environ.get("ESTATE_NOTIFY_CHANNEL", "founder-telegram")
HTTP_TIMEOUT_S = int(os.environ.get("ESTATE_GITOPS_HTTP_TIMEOUT_SECONDS", "20"))

# The marker the comment is found by. One pull request has one drift comment and
# this is how the sensor updates it instead of adding to it; a thread per poll
# would bury the cause under its own symptoms.
COMMENT_MARKER = "<!-- estate-drift -->"
# The flux-system namespace owns the Kustomizations; a HelmRelease lives in the
# namespace it deploys into. Both are overridable so no file names a machine.
FLUX_NAMESPACE = os.environ.get("ESTATE_FLUX_NAMESPACE", "flux-system")


# --- step 1: read the drifts Flux already writes -----------------------------


def _ready_condition(obj: dict) -> Optional[dict]:
    for c in (obj.get("status") or {}).get("conditions") or []:
        if c.get("type") == "Ready":
            return c
    return None


def drifts_from(objects: Iterable[dict]) -> List[Dict[str, Any]]:
    """Every object Flux is not happy with, as one flat list of findings.

    Four readings, each deliberate:

    * A `Ready` condition that is `True` is not a drift. A sensor that reports a
      healthy estate is a sensor nobody reads (LAW 28).
    * A `Ready` condition that is not `True` is a drift, and its `reason` is
      Flux's own message -- never a summary this module wrote. A paraphrase is a
      claim about what Flux said.
    * NO `Ready` CONDITION AT ALL IS NOT A DRIFT. An object that was just applied
      has not reported yet, and reading that silence as breakage is how a watcher
      pages on every single apply. `UNKNOWN` is not a failure (crew#656 phase 0).
    * A SUSPENDED OBJECT IS NOT A DRIFT, WHATEVER ITS LAST STATUS SAYS. Measured
      2026-09-13: `temporal` carries `spec.suspend: true` on the founder's word
      (crew#284, "what I spec'd was not what was built"), so Flux stopped
      reconciling it on 2026-08-30 -- while its last recorded condition stayed
      `HealthCheckFailed / InProgress` and its old pods kept running. Reporting
      that as a drift is reporting a decision as a defect, which is how a watcher
      teaches people to ignore it.
    """
    out: List[Dict[str, Any]] = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        spec = obj.get("spec") or {}
        if spec.get("suspend") is True:
            continue
        cond = _ready_condition(obj)
        if cond is None or cond.get("status") == "True":
            continue
        meta = obj.get("metadata") or {}
        kind = obj.get("kind") or ""
        ns = meta.get("namespace") or FLUX_NAMESPACE
        name = meta.get("name") or ""
        if not name:
            continue
        out.append(
            {
                "object": f"{ns}/{name}",
                "kind": kind,
                "namespace": ns,
                "name": name,
                "reason_code": cond.get("reason") or "",
                "reason": (cond.get("message") or cond.get("reason") or "").strip(),
            }
        )
    return out


def drift_fingerprint(drift: dict) -> str:
    """One id for one drift, built from identity and cause and never from time.

    The same object failing for the same reason is the same drift however long it
    has been broken; a different reason is a new one worth saying out loud. This
    is `holmes_watch.alert_fingerprint`'s rule, and it is what stops one broken
    object being reported every poll for a day.
    """
    key = f"{drift.get('object', '')}|{drift.get('kind', '')}|{drift.get('reason', '')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# --- step 2: isolate the cause, or say the cause is unknown ------------------


def repo_root() -> Path:
    """The checkout this module ships in, found from the file, never typed."""
    return Path(__file__).resolve().parents[2]


def helmrelease_owner(drift: dict) -> Optional[str]:
    """The file in this tree that declares this HelmRelease, or None.

    A HelmRelease is a document in a YAML file, and Flux names the object but not
    the file. The file is what git history can attribute to a commit, so this is
    the join between what the cluster says and what the repository did.
    """
    if drift.get("kind") != "HelmRelease":
        return None
    name = drift.get("name") or ""
    root = repo_root()
    for path in sorted(root.glob("platform/**/*.yaml")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "kind: HelmRelease" in text and f"name: {name}" in text:
            return str(path.relative_to(root))
    return None


def kustomization_owner(drift: dict) -> Optional[str]:
    """The file declaring a Kustomization with this name, or None.

    Flux's Kustomization objects are generated from the tree in several places
    (`clusters/*/estate.yaml` among them) and a name that appears nowhere in the
    tree genuinely has no owner. Returning None there is the honest answer.
    """
    name = drift.get("name") or ""
    root = repo_root()
    for path in sorted(root.glob("clusters/**/*.yaml")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "kind: Kustomization" in text and f"name: {name}" in text:
            return str(path.relative_to(root))
    return None


def git_history(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """The last commit that touched each file in the tree, with its pull request.

    One `git log` walk rather than one call per file. The pull request is read off
    the squash-merge subject, which is how this repository writes it:
    `... (#3284)`. A commit with no such suffix contributes its sha and no pull
    request, and the caller must not invent one.

    The format is `<sha>|<subject>` on one line, then the file names, then a blank
    line -- measured against this repository's own log. The first commit that names
    a file wins, which is the newest, because the walk is newest-first.
    """
    root = root or repo_root()
    try:
        r = subprocess.run(
            [
                "git",
                "log",
                "--no-merges",
                "--pretty=format:%H|%s",
                "--name-only",
                "origin/main",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}

    history: Dict[str, Dict[str, Any]] = {}
    sha = subject = ""
    for raw in r.stdout.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if "|" in line and len(line.split("|", 1)[0]) == 40:
            sha, subject = line.split("|", 1)
            continue
        if not sha:
            continue
        if line not in history:
            pr = None
            marker = subject.rfind("(#")
            if marker != -1:
                tail = subject[marker + 2 :].rstrip(")").strip()
                if tail.isdigit():
                    pr = int(tail)
            history[line] = {"sha": sha, "pull_request": pr, "title": subject}
    return history


def attribute(
    drifts: Sequence[Dict[str, Any]],
    history: Dict[str, Dict[str, Any]],
    owner: Callable[[dict], Optional[str]],
) -> List[Dict[str, Any]]:
    """Fill in `file`, `commit` and `pull_request` for each drift, or say why not.

    Every input drift comes out the other side. A drift whose owning file cannot
    be found keeps `pull_request: None` and carries the sentence explaining it --
    never dropped, and never guessed at (LAW 29, spec 2026-09-13).
    """
    out: List[Dict[str, Any]] = []
    for drift in drifts:
        d = dict(drift)
        d.setdefault("pull_request", None)
        d.setdefault("commit", None)
        d.setdefault("file", None)

        path = owner(d)
        if not path:
            d["reason"] = d.get("reason") or ""
            d["unattributed"] = f"no file in this tree owns {d.get('object', '')}"
            out.append(d)
            continue

        d["file"] = path
        entry = history.get(path) or {}
        d["commit"] = entry.get("sha")
        d["pull_request"] = entry.get("pull_request")
        if d["commit"] is None:
            d["unattributed"] = f"{path} is not in the history this estate can read"
        elif d["pull_request"] is None:
            d["unattributed"] = (
                f"{path} was last changed by {str(d['commit'])[:12]}, which names no pull request"
            )
        out.append(d)
    return out


# --- step 3: one comment per pull request ------------------------------------


def group_by_pull_request(drifts: Sequence[dict]) -> Dict[int, List[dict]]:
    """Group attributed drifts by pull request; unattributed ones group at 0.

    Key 0 is "the estate could not file this", and it is kept separate on purpose:
    a pull request number is a place to post, and there is no place 0.
    """
    groups: Dict[int, List[dict]] = {}
    for d in drifts:
        pr = d.get("pull_request")
        key = int(pr) if isinstance(pr, int) and pr > 0 else 0
        groups.setdefault(key, []).append(d)
    return groups


def comment_body(pull_request: int, drifts: Sequence[dict]) -> str:
    """The text posted for one pull request. Never claims a cause it cannot name."""
    lines = [COMMENT_MARKER, f"**{SENDER}**", ""]
    if pull_request:
        lines.append(
            f"This pull request (#{pull_request}) appears to have left "
            f"{len(drifts)} object{'s' if len(drifts) != 1 else ''} in this estate "
            "not reconciled:"
        )
    else:
        lines.append(
            f"{len(drifts)} object(s) in this estate are not reconciled, and the "
            "estate cannot yet say which change caused them:"
        )
    lines.append("")
    for d in drifts:
        lines.append(
            f"- `{d.get('object', '?')}` ({d.get('kind', '?')}) -- {d.get('reason', '')}"
        )
        if d.get("file"):
            lines.append(f"  - file: `{d['file']}`")
        if d.get("commit"):
            lines.append(f"  - commit: `{str(d['commit'])[:12]}`")
        # A drift with no file, no commit or no pull request must say so rather
        # than render as a bare bullet a reader would take for a complete finding.
        if not d.get("file") or not d.get("commit") or not d.get("pull_request"):
            why = (
                d.get("unattributed")
                or "the estate cannot yet say which change caused this"
            )
            lines.append(f"  - **unknown:** {why}")
    lines.append("")
    lines.append(
        "Read from the cluster's own Flux objects; the cause is the file above, "
        "from this branch's history. This comment is updated in place."
    )
    return "\n".join(lines)


def drift_payload(
    objects: Iterable[dict],
    history: Optional[Dict[str, Dict[str, Any]]] = None,
    owners: Optional[Dict[str, Callable[[dict], Optional[str]]]] = None,
) -> Dict[str, Any]:
    """The whole unit of work: read, fingerprint, attribute, group.

    Returned as one document so the sensor, the CLI and the tests grade the same
    function. `attributed` counts the drifts that name a pull request; a drift the
    estate cannot file is in `unattributed` and is still a drift.
    """
    owners = owners or {
        "HelmRelease": helmrelease_owner,
        "Kustomization": kustomization_owner,
    }
    history = git_history() if history is None else history

    found = drifts_from(objects)
    for d in found:
        d["fingerprint"] = drift_fingerprint(d)
    filed = attribute(
        found, history, lambda d: (owners.get(d.get("kind")) or (lambda _d: None))(d)
    )
    groups = group_by_pull_request(filed)

    return {
        "summary": {
            "drifts": len(filed),
            "attributed": sum(1 for d in filed if d.get("pull_request")),
            "unattributed": len(groups.get(0, [])),
            "pull_requests": sorted(k for k in groups if k),
        },
        "drifts": filed,
    }


def publish(
    title: str, body: str, url: str = APPRISE_URL, channel: str = NOTIFY_CHANNEL
) -> None:
    """Deliver through the notify layer the estate already runs.

    Same endpoint, same payload shape and same sender rule as `holmes_watch`: one
    channel, several programs, and every message names who is speaking.
    """
    # `requests`, the same client holmes_watch uses, so the estate has one HTTP
    # path and not two. It also removes the reason S310 exists: urlopen will follow
    # a `file:` URL, and this endpoint is http inside the cluster. The scheme is
    # checked anyway, because a caller that mistypes an env var should get a
    # sentence rather than a request.
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"refusing to deliver over {parsed.scheme or 'a schemeless'} URL: "
            f"{url!r} is not an http endpoint"
        )
    r = requests.post(
        f"{url.rstrip('/')}/notify/{channel}",
        json={"title": title, "body": body, "type": "warning", "format": "text"},
        timeout=HTTP_TIMEOUT_S,
    )
    r.raise_for_status()
