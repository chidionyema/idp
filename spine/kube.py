"""Read a Flux object's own status, in-cluster, read-only.

The spine's answer to "did that reconciliation actually succeed?" is not a second opinion:
it is the object's own status, read from the API server. That is the estate's decision
register's position (dec:spine-woken-verification, mode machine, decided_by
cap:intent/flux-status): the workflow that runs the check is the trigger, not the decider,
and the check is a state fetch with a deterministic answer.

The reader is deliberately small: a service-account token, the cluster CA, and three GETs.
It never writes. It never shells out. There is no kubectl in the image and no second
credential path.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

# Where the kubelet mounts the pod's service account.
SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"
TOKEN_FILE = os.path.join(SA_DIR, "token")
CA_FILE = os.path.join(SA_DIR, "ca.crt")

# The Flux kinds the spine reads, and where each lives in the API.
FLUX_RESOURCES = {
    "Kustomization": ("kustomize.toolkit.fluxcd.io", "v1", "kustomizations"),
    "HelmRelease": ("helm.toolkit.fluxcd.io", "v2", "helmreleases"),
    "GitRepository": ("source.toolkit.fluxcd.io", "v1", "gitrepositories"),
}


class KubeError(RuntimeError):
    """The API server could not be read, or said something unusable."""


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class KubeReader:
    """A read-only client for the objects the spine verifies."""

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[str] = None,
        token: Optional[str] = None,
        ca_file: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.host = host or os.environ.get(
            "KUBERNETES_SERVICE_HOST", "kubernetes.default.svc"
        )
        self.port = port or os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        self._token = token
        self._ca_file = ca_file or CA_FILE
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "KubeReader":
        return cls()

    @property
    def token(self) -> str:
        if self._token is None:
            try:
                self._token = _read(TOKEN_FILE).strip()
            except OSError as exc:
                raise KubeError(
                    "no service account token at %s: %s" % (TOKEN_FILE, exc)
                ) from exc
        return self._token

    def _context(self) -> ssl.SSLContext:
        try:
            return ssl.create_default_context(cafile=self._ca_file)
        except OSError as exc:
            raise KubeError("no cluster CA at %s: %s" % (self._ca_file, exc)) from exc

    def get(self, path: str) -> Dict[str, Any]:
        url = "https://%s:%s%s" % (self.host, self.port, path)
        request = urllib.request.Request(url, method="GET")  # noqa: S310 - https to the api server
        request.add_header("Authorization", "Bearer %s" % self.token)
        request.add_header("Accept", "application/json")
        try:
            # The scheme is fixed to https by construction; the API server is the only host.
            with urllib.request.urlopen(  # noqa: S310 - https to the api server
                request, context=self._context(), timeout=self.timeout
            ) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise KubeError("not found: %s" % path) from exc
            raise KubeError("api server said %s for %s" % (exc.code, path)) from exc
        except urllib.error.URLError as exc:
            raise KubeError("api server unreachable: %s" % exc) from exc
        try:
            return json.loads(body)
        except ValueError as exc:
            raise KubeError("api server returned non-JSON: %s" % exc) from exc

    def get_object(self, kind: str, namespace: str, name: str) -> Dict[str, Any]:
        if kind not in FLUX_RESOURCES:
            raise KubeError("kind %r is not one the spine verifies" % kind)
        group, version, plural = FLUX_RESOURCES[kind]
        path = "/apis/%s/%s/namespaces/%s/%s/%s" % (
            group,
            version,
            namespace,
            plural,
            name,
        )
        return self.get(path)

    def status_of(self, kind: str, namespace: str, name: str) -> Dict[str, Any]:
        """The verdict on one object's reconcile.

        Four answers, and they are the only four: verified, failed, stale, or missing.

          verified  the object is Ready and the applied revision is the attempted one.
          failed    the object is not Ready; the condition carries the reason.
          stale     the applied revision is behind the attempted one, so the event's
                    reconciliation has not landed yet.
          missing   the object is gone. A vanished object is not a passing verdict, and
                    saying so is the whole point of asking.
        """
        try:
            obj = self.get_object(kind, namespace, name)
        except KubeError as exc:
            if "not found" in str(exc):
                return {
                    "found": False,
                    "ready": False,
                    "verdict": "missing",
                    "reason": "NotFound",
                    "message": str(exc),
                    "revision": "",
                }
            return {
                "found": False,
                "ready": False,
                "verdict": "unreadable",
                "reason": "Unreadable",
                "message": str(exc),
                "revision": "",
            }
        return verdict_from_object(obj)


def verdict_from_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Grade a Flux object's status. The whole check, with no I/O in it."""
    status = obj.get("status") or {}
    conditions = status.get("conditions") or []
    ready = None
    reason = ""
    message = ""
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        if condition.get("type") == "Ready":
            ready = condition.get("status")
            reason = str(condition.get("reason") or "")
            message = str(condition.get("message") or "")
            break
    applied = str(status.get("lastAppliedRevision") or "")
    attempted = str(status.get("lastAttemptedRevision") or "")
    revision = applied or attempted

    if ready == "True":
        if attempted and applied and applied != attempted:
            # Ready says yes, but the applied revision is behind the attempted one: the
            # event's reconciliation has not landed yet, and saying "verified" would be
            # saying something the cluster has not said.
            return {
                "found": True,
                "ready": False,
                "verdict": "stale",
                "reason": reason or "Stale",
                "message": message,
                "revision": applied,
                "attemptedRevision": attempted,
            }
        return {
            "found": True,
            "ready": True,
            "verdict": "verified",
            "reason": reason or "ReconciliationSucceeded",
            "message": message,
            "revision": revision,
            "attemptedRevision": attempted,
        }
    if ready in ("False", "Unknown"):
        return {
            "found": True,
            "ready": False,
            "verdict": "failed",
            "reason": reason
            or ("ReconciliationFailed" if ready == "False" else "Unknown"),
            "message": message,
            "revision": revision,
            "attemptedRevision": attempted,
        }
    return {
        "found": True,
        "ready": False,
        "verdict": "failed",
        "reason": reason or "NoReadyCondition",
        "message": message,
        "revision": revision,
        "attemptedRevision": attempted,
    }
