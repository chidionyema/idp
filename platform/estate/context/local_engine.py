"""local_engine -- the laptop's door to the ONE context engine.

THE ENGINE IS ONE. gortex (zzet/gortex v0.64.11, Apache-2.0) is the estate's context engine:
retrieval, ranking, symbol resolution and impact selection are its job, and the estate's
layers do not duplicate them (AGENTS.md 6). This module is a CLIENT of that engine -- it
speaks the engine's CLI and translates its answer. It scores nothing.

TWO DOORS, ONE ENGINE. In the cluster the engine is private: the broker holds its token and
is the only thing that can reach it (platform/estate/context/broker.py). On a laptop there is
no cluster and no token, so the developer fallback daemon -- the same engine, running locally,
tracking a checkout -- is the door. The laptop daemon is the estate's FALLBACK, not the
default route, and this client says which door it used in every answer it builds.

FRESHNESS IS READ, NOT ASSUMED. The engine publishes, per repository, the commit its index
was built from and the commit the tree is at. This client reads both and hands them to the
policy, which compares them. Nothing here decides whether a stale index may be served; that
decision belongs to the broker's freshness_decision, and there is one of those.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Sequence

from .broker import EngineError, unwrap_engine_envelope


class EngineUnavailable(RuntimeError):
    """The engine is not there, or would not answer. The caller refuses; it never guesses."""


class LocalGortexEngine:
    """A client of the local gortex daemon, over the engine's own CLI.

    The daemon is not an HTTP server on a laptop, so the CLI is the transport. In the cluster
    the same engine is reached over HTTP by the broker's EngineClient -- one engine, two
    transports, and both of them dumb: they ask, and they translate.
    """

    def __init__(
        self,
        repo: str,
        *,
        binary: str = "gortex",
        timeout: float = 120.0,
        home: str | None = None,
    ):
        self.repo = os.path.abspath(repo)
        self.binary = binary
        self.timeout = timeout
        self.home = home

    # --- plumbing -------------------------------------------------------------------------------
    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.home:
            env["HOME"] = self.home
        env.setdefault("NO_COLOR", "1")
        return env

    def _run(self, args: Sequence[str]) -> str:
        exe = shutil.which(self.binary)
        if not exe:
            raise EngineUnavailable(
                f"{self.binary} is not on PATH; the laptop fallback daemon is not installed"
            )
        try:
            proc = subprocess.run(  # noqa: S603 -- list form, no shell
                [exe, *args],
                cwd=self.repo,
                env=self._env(),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineUnavailable(
                f"the engine did not answer within {self.timeout}s"
            ) from exc
        except OSError as exc:
            raise EngineUnavailable(f"the engine could not be run: {exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:400]
            raise EngineUnavailable(
                f"the engine refused {args[0] if args else 'the request'}: {detail}"
            )
        return proc.stdout

    # --- the engine's surface -------------------------------------------------------------------
    def working_set(
        self,
        task: str,
        token_budget: int,
        *,
        paths: Sequence[str] = (),
        view: str | None = None,
    ) -> dict[str, Any]:
        """Ask the engine for its ranked working set on a task. That is all this client does.

        The engine's own budget is the request; the plan's ceiling is the broker's business.
        """
        args: dict[str, Any] = {"task": task, "token_budget": int(token_budget)}
        if paths:
            args["paths"] = [str(p) for p in paths]
        if view:
            args["view"] = view
        raw = self._run(
            [
                "call",
                "smart_context",
                "--json",
                json.dumps(args),
                "--index",
                self.repo,
                "--format",
                "json",
            ]
        )
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise EngineUnavailable(
                "the engine answered with something that is not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise EngineUnavailable("the engine answered with an unexpected shape")
        # The engine's tool answers travel in the MCP result envelope on both transports (the
        # REST surface and the CLI's JSON output). Opening it here -- in the ONE place that
        # speaks the engine's wire format -- is what keeps a bare-envelope answer from being
        # mistaken for an answer with no files in it.
        try:
            unwrapped = unwrap_engine_envelope("smart_context", payload)
        except EngineError as exc:
            raise EngineUnavailable(str(exc)) from exc
        if not isinstance(unwrapped, dict):
            raise EngineUnavailable("the engine answered with an unexpected shape")
        return unwrapped

    def freshness(self) -> dict[str, Any]:
        """What the engine knows about this repository's index: which commit, and is it current.

        `gortex repos --json` reports, per repository: the git HEAD, the commit the index was
        built from, when it was built, and whether it is stale. This client reads those fields
        and NOTHING ELSE -- the policy decides what a stale index means.
        """
        raw = self._run(["repos", "--json"])
        try:
            rows = json.loads(raw)
        except ValueError as exc:
            raise EngineUnavailable(
                "the engine's repository list was not JSON"
            ) from exc
        if not isinstance(rows, list):
            raise EngineUnavailable(
                "the engine's repository list had an unexpected shape"
            )
        best: dict[str, Any] | None = None
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "")
            if os.path.abspath(path) == self.repo:
                best = row
                break
        if best is None:
            raise EngineUnavailable(
                f"the engine is not tracking {self.repo}; run `gortex track {self.repo}`"
            )
        return {
            "path": best.get("path"),
            "head_commit": best.get("head_commit"),
            "indexed_commit": best.get("indexed_commit"),
            "indexed": bool(best.get("indexed")),
            "stale": bool(best.get("stale")),
            "last_indexed": best.get("last_indexed"),
            "freshness_scope": best.get("freshness_scope"),
            "branch": best.get("branch"),
        }

    def version(self) -> str:
        """The engine's own version string, for the plan's provenance."""
        try:
            raw = self._run(["status"])
        except EngineUnavailable:
            return "unknown"
        for line in raw.splitlines():
            if "v0." in line:
                return (
                    line.strip().split()[1] if len(line.split()) > 1 else line.strip()
                )
        return "unknown"
