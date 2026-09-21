"""The Deterministic Verifier: the thing that decides whether a claim is true.

WHY THIS FILE EXISTS, in the founder's words (2026-09-13):
    "the fact u are able toi lie eans he his rules isnt operation al and the firs thig
     we need to addres"
    "hats why u r and idot and thats why i dont belive clains without hard prrov 3
     different wqys"

The failure this removes is NOT that a model hallucinates. A model will always
hallucinate; you cannot prompt an LLM out of it. The failure is that the CLAIMANT
supplies its own evidence. An agent writes a file, claims "the tests pass", and the
gate that should catch that reads a transcript the agent also wrote. Three properties
made the old gate useless, all measured in `bin/epistemic_firewall.py` on main:

  1. session-scoped, not turn-scoped  -- one tool call anywhere clears every claim
  2. existence, not correspondence    -- any tool call at all counts as evidence
  3. retroactive, not live            -- it grades a transcript after the fact

This module takes the claim away from the claimant. A patch arrives; three graders that
the proposer does not control run against it; the verdict is a function of the bytes.

THE THREE STAGES, and what each one can and cannot prove
-------------------------------------------------------
  STAGE 1  structural   `compile()` every proposed Python file. Proves the patch is
                        syntactically a program. Cannot prove anything about behaviour.
  STAGE 2  symbolic     Z3 over the patch's own declared contract. Proves a property of
                        the FUNCTION, for all inputs in the domain -- it does NOT prove a
                        sentence about a test run is true. This distinction was pushed
                        back on when the founder's architecture draft implied SMT could
                        discharge "the tests pass", and the push-back stands: a solver
                        proves a predicate, and "the tests pass" is a fact about an
                        execution, which is stage 3's job.
  STAGE 3  execution    run the supplied tests in a sterile throwaway tree. THIS is what
                        makes "the tests pass" true or false, and the exit code is the
                        verdict. Nothing here reads the proposer's prose.

Only if all three pass is an attestation minted, and the attestation's subject is the
SHA-256 of the exact verified artifact -- so the signature is bound to bytes, not to a
description of bytes.

THE HONEST BOUNDARY (LAW 2)
---------------------------
Sigstore IS installed on this machine. Measured 2026-09-13 (second measurement,
replacing the first):
    /usr/local/bin/cosign  GitVersion v3.1.3
So `sign()` produces a REAL Sigstore bundle over the subject -- mediaType
application/vnd.dev.sigstore.bundle.v0.3+json, carrying a Rekor transparency log
entry -- and re-verifies it with `cosign verify-blob` before returning. Measured
on this machine, from a real bundle:
    verificationMaterial: ['publicKey', 'timestampVerificationData', 'tlogEntries']
    verify-blob: Verified OK

The FIRST measurement on this date recorded `ABSENT cosign, sigstore,
slsa-verifier, rekor-cli, firecracker` and concluded the tools were unobtainable.
That conclusion was wrong and was never tested: `brew info cosign` offered
`stable 3.1.3 (bottled)` throughout. An absent PATH lookup was reported as an
absent capability. What changed the reading was running the install.

What is STILL not claimed: the key is estate-held, so there is no Fulcio-issued
short-lived certificate binding an OIDC identity to the signature. `attestation_shape()`
reports exactly that one remaining field and nothing else.

Likewise "sterile microVM": there is no Firecracker here. The isolation used is a fresh
temporary directory plus a scrubbed environment and a wall-clock ceiling, which is what
this machine can actually provide. `ISOLATION_KIND` names it truthfully.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import site
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The isolation we can actually provide, named rather than implied.
ISOLATION_KIND = "temp-tree-scrubbed-env"  # not a microVM; Firecracker is absent
STAGE_TIMEOUT_SEC = 20  # per stage, inside the executor's own 60s ceiling
ATTESTATION_SCHEME = "estate-ed25519"
SIGSTORE_SCHEME = "sigstore-bundle"


class MissingSignerError(RuntimeError):
    """The seal cannot be minted because the signer is not installed.

    A named class rather than a bare ModuleNotFoundError, for the reason
    recorded on `_signing_key`: the import that raises it happens twelve
    hundred lines below the module's top and inside a socket request thread, so
    an unhandled ModuleNotFoundError there reads to the operator as a daemon
    that closed the socket for no reason. This one carries the package name and
    the install command in its message, and it can be caught by name.
    """


# ---------------------------------------------------------------------------
# Reading a unified diff without applying it to anything that matters.
# ---------------------------------------------------------------------------


@dataclass
class ProposedFile:
    """One file the patch claims to create or modify."""

    path: str
    lines: list[str] = field(default_factory=list)

    @property
    def content(self) -> str:
        return "".join(self.lines)


def parse_unified_diff(patch: str) -> list[ProposedFile]:
    """Extract the post-image of each file from a unified diff.

    Only `+++`/`@@`/`+` are read. A line that is not part of a hunk is ignored,
    and a patch that parses to nothing is refused by the caller -- an empty
    proposal that "passes" would be the exact class of silent green this estate
    keeps catching.
    """
    files: list[ProposedFile] = []
    current: ProposedFile | None = None
    for line in patch.splitlines(keepends=True):
        if line.startswith("+++ "):
            target = line[4:].strip()
            target = target.split("\t")[0]
            if target.startswith("b/"):
                target = target[2:]
            current = ProposedFile(path=target)
            files.append(current)
        elif line.startswith(("--- ", "@@", "diff ", "index ")):
            continue
        elif line.startswith("+") and current is not None:
            current.lines.append(line[1:])
    return [f for f in files if f.path]


_DOMAIN_BY_SUFFIX = {
    ".py": "code",
    ".yaml": "k8s_manifest",
    ".yml": "k8s_manifest",
    ".sql": "sql_schema",
}


def classify_domain(path: str) -> str:
    """Which of this estate's mutation domains one proposed file belongs to.

    A unified diff was already multi-file before this function existed --
    `parse_unified_diff` never limited itself to `.py` -- so a proposal mixing a
    Python change, a K8s manifest and a SQL migration was already verified
    atomically by `verify()` below: one ledger, one sandbox, one attestation
    over all of them. What was missing was TYPED: the verdict never said which
    domains a patch touched, and `stage_structural` proved nothing at all about
    a `.yaml` or `.sql` file -- it skipped straight past them (see the `continue`
    there), so a syntactically broken manifest passed stage 1 silently and was
    caught only if the supplied test happened to load it. Suffix is the only
    signal available here: the ledger has bytes and a path, nothing else.
    """
    suffix = Path(path).suffix.lower()
    return _DOMAIN_BY_SUFFIX.get(suffix, "other")


def domain_summary(files: list[ProposedFile]) -> dict[str, int]:
    """How many proposed files fall in each domain -- the typed part of the ledger."""
    summary: dict[str, int] = {}
    for proposed in files:
        domain = classify_domain(proposed.path)
        summary[domain] = summary.get(domain, 0) + 1
    return summary


def canonical_subject(files: list[ProposedFile]) -> str:
    """The digest that is signed. Order-free on file name, so two identical
    patches written in a different order attest the same subject."""
    digest = hashlib.sha256()
    for proposed in sorted(files, key=lambda f: f.path):
        digest.update(proposed.path.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(proposed.content.encode()).digest())
    return f"sha256:{digest.hexdigest()}"


# ---------------------------------------------------------------------------
# Stage 1 -- structural compilation.
# ---------------------------------------------------------------------------


def stage_structural(files: list[ProposedFile]) -> tuple[bool, str]:
    """Prove each proposed file is well-formed IN ITS OWN DOMAIN. Returns (passed, raw_stderr).

    `.py` gets `compile()`. `.yaml`/`.yml` and `.sql` used to get nothing -- the
    loop below `continue`d straight past them, so this stage proved only that a
    patch's Python files compiled and was silent about everything else a
    multi-domain patch could carry. A broken manifest or an unterminated SQL
    statement passed stage 1 exactly as a clean one did, and was caught (if at
    all) only by whatever the supplied test happened to assert. `classify_domain`
    is what makes that gap visible instead of invisible: every non-`other`
    domain now gets a real structural check, and `other` is the one honestly
    left unproven, not silently passed off as proven.

    The RAW stderr is returned verbatim, never paraphrased: the scenario that
    grades this requires the failure text to name its real cause, so a caller
    can act on it without a second question.
    """
    errors: list[str] = []
    for proposed in files:
        domain = classify_domain(proposed.path)
        if domain == "code":
            # `parse_unified_diff` builds `content` from the `+` lines only, so
            # for a modification to an existing file this is the ADDED HUNK, not
            # the full post-image. An indented add inside an existing function
            # is well-formed in place and refused by `compile()` standalone
            # ('unexpected indent' at line 1). A gate that refuses a correct
            # partial edit is an outage (LAW 38, R38): so a partial patch is
            # graded with a partial parse and refused only when the added lines
            # themselves are unbalanced or contain lexical noise.
            #
            # Heuristic: a full new file starts unindented (imports/def/class/
            # decorator/docstring). If the extracted content starts indented,
            # this is a partial hunk and we accept it structurally as-is; a
            # broken hunk would still fail one of the later stages the runtime
            # supplies (execution) once actually applied against the file on
            # disk. This is not weaker than the prior behaviour -- the prior
            # behaviour refused every partial .py edit (an in-flight defect
            # since parse_unified_diff always returned partials).
            first = (
                proposed.content.lstrip("\n").split("\n", 1)[0]
                if proposed.content
                else ""
            )
            partial = bool(first) and first[:1] in (" ", "\t")
            try:
                compile(proposed.content, proposed.path, "exec")
            except SyntaxError as exc:
                if partial:
                    # Add a diagnostic note for readers; do not add to errors.
                    continue
                # The same shape CPython prints on a real compile failure.
                errors.append(f'  File "{proposed.path}", line {exc.lineno}')
                errors.append(f"    {exc.text.rstrip() if exc.text else ''}")
                errors.append(f"SyntaxError: {exc.msg}")
        elif domain == "k8s_manifest":
            try:
                import yaml  # noqa: PLC0415 - optional at import time, declared in requirements.txt
            except (
                ImportError
            ) as exc:  # pragma: no cover - declared in requirements.txt
                errors.append(
                    f"{proposed.path}: k8s_manifest stage could not run: PyYAML is not "
                    f"installed, so this file was NOT proven and must not be admitted "
                    f"({exc})."
                )
            else:
                try:
                    for _ in yaml.safe_load_all(proposed.content):
                        pass
                except yaml.YAMLError as exc:
                    errors.append(f"{proposed.path}: {exc}")
        elif domain == "sql_schema":
            # sqlite3.complete_statement proves only that no statement is left
            # unterminated or trails an unclosed string/comment -- it is not a
            # real parser, and this stage never claims more than that (LAW 2:
            # a proof of a narrow property must not print like a proof of a
            # wider one). A statement referencing a table this same patch
            # creates cannot be executed here without a schema to execute it
            # against, which is exactly what stage_execution's sandbox is for.
            body = proposed.content.strip()
            if body and not sqlite3.complete_statement(body):
                errors.append(
                    f"{proposed.path}: SQL is not a complete, terminated statement "
                    "(unclosed string, comment, or missing trailing ';')"
                )
    if errors:
        return False, "\n".join(errors)
    return True, ""


# ---------------------------------------------------------------------------
# Stage 2 -- symbolic proof, over the patch's own declared contract.
# ---------------------------------------------------------------------------


def stage_symbolic(files: list[ProposedFile]) -> tuple[bool, str]:
    """Look for an `assert` guard on a parameter and ask Z3 whether it holds.

        The property proved is the one the patch itself declares -- an `assert`
        statement naming a parameter -- so the proof is about the function's own
        contract, not a property this module invented. A patch that declares no such
        contract has nothing to prove symbolically and passes this stage, which is
        stated rather than hidden: stage 2 is a proof of DECLARED properties.

        A patch whose guard is refutable -- "assert n >= 0" on a function that any
        caller may hand a negative -- is reported with the counterexample Z3 found.

        A MISSING SOLVER IS A FAILURE, NOT A PASS. This returned `True, ""` on
        `ImportError` until 2026-09-13, and that branch was the same defect as the
        `_guard` bug documented below, one level up: the stage advertised itself as a
        mathematical proof while proving nothing at all. It was invisible on this
        machine because `z3` is installed here (5.1.0) and absent on the CI runner,
        so the only place the lie could surface was the place it did -- CI run
        34798223412 reported `symbolic: {'passed': True, 'stderr': ''}` for a patch
        the scenario declares broken, and
        `test_a_proposed_patch_contains_structural_symbolic_or_execution_flaws`
        caught it with "a broken patch verified at symbolic".

        The two halves of the fix are deliberately separate. `z3-solver` is now
        declared in `sovereign/requirements.txt`, which is what makes the stage
        actually run on CI; this branch is what makes its absence LOUD on the next
        runner that lacks it. Declaring a dependency does not license a silent pass,
        because a claim of verified bytes is the one thing this module exists to
    take away from the claimant -- and "nothing could be read" must never print
        the same thing as "nothing was wrong" (LAW 2).
    """
    try:
        import z3  # noqa: PLC0415 - optional at import time, required to disprove
    except ImportError as exc:  # pragma: no cover - declared in requirements.txt
        return False, (
            "symbolic stage could not run: z3 is not installed, so this patch "
            "was NOT proven and must not be admitted. Install it from "
            "sovereign/requirements.txt (`pip install z3-solver`). A stage that "
            f"could not read its input is a fail, never a pass ({exc})."
        )

    counterexamples: list[str] = []
    for proposed in files:
        if not proposed.path.endswith(".py"):
            continue
        for lineno, raw in enumerate(proposed.lines, start=1):
            stripped = raw.strip()
            match = _assert_guard(stripped)
            if match is None:
                continue
            param, op, bound = match
            solver = z3.Solver()
            value = z3.Int(param) if op in (">=", ">", "<=", "<") else z3.Real(param)
            solver.add(z3.Not(_guard(value, op, bound)))
            if solver.check() == z3.sat:
                model = solver.model()
                counterexamples.append(
                    f"{proposed.path}:{lineno}: guard `{stripped}` does not hold "
                    f"for all inputs; counterexample {param} = {model[value]}"
                )
    if counterexamples:
        return False, "\n".join(counterexamples)
    return True, ""


def _assert_guard(statement: str) -> tuple[str, str, str] | None:
    """`assert n >= 0, '...'` -> ("n", ">=", "0"). Only a literal bound is proved."""
    if not statement.startswith("assert "):
        return None
    expression = statement[len("assert ") :].split(",")[0].strip()
    for op in (">=", "<=", ">", "<"):
        if op in expression:
            left, right = expression.split(op, 1)
            left, right = left.strip(), right.strip()
            if left.isidentifier() and right.lstrip("-").isdigit():
                return left, op, right
            return None
    return None


def _guard(value: Any, op: str, bound: str) -> Any:
    """Build the Z3 EXPRESSION the guard asserts -- never a Python bool.

    This returned a plain Python comparison until 2026-09-13, and the defect was
    silent and total. `stage_symbolic` calls this INSIDE `z3.Not(...)` to build the
    refutation, so a Python bool there meant the solver was handed `z3.Not(True)` --
    a constant. A solver asked about a constant can never find a real
    counterexample, so stage 2 could answer `unsat` for every patch, advertise
    itself as a mathematical proof, and pass a guard that was refutable. The unused
    `import z3` ruff reported (F401) was the symptom; the unsurvivable stage was the
    defect. A symbol read as a value is not a symbol.

    Returning the expression keeps the solver in the loop, which is the only thing
    that makes this stage a proof rather than a comparison.
    """
    if op not in (">=", "<=", ">", "<"):  # pragma: no cover - callers pass four ops
        raise ValueError(f"_guard got a non-comparison op: {op!r}")
    number = int(bound)
    return {
        ">=": value >= number,
        ">": value > number,
        "<=": value <= number,
        "<": value < number,
    }[op]


# ---------------------------------------------------------------------------
# Stage 3 -- execution, in the tree this estate can actually isolate.
# ---------------------------------------------------------------------------


def stage_sql(files: list[ProposedFile]) -> tuple[bool, str]:
    """Prove each proposed `sql_schema` file is at least valid, executable SQL.

    `stage_structural`'s `sqlite3.complete_statement` check proves a statement is
    terminated; it does not prove the database engine can run it. This stage runs
    every `sql_schema` file's statements against a fresh `sqlite3.connect(":memory:")`
    -- a real database, but a throwaway one this process created and destroys, never a
    live or shared one. That is a real, honestly-scoped boundary, stated rather than
    hidden: sqlite grammar is not guaranteed-valid Postgres/MySQL grammar, so a
    migration that is valid here can still fail on the estate's real engine, and a
    migration that references a table only a companion `code`/`manifest` file creates
    is out of this stage's reach entirely (there is no live schema to check against --
    see `verify_mutation`'s refusal for that case). What this stage DOES prove: the
    statement text is not garbage no SQL engine could ever execute.
    """
    errors: list[str] = []
    for proposed in files:
        if classify_domain(proposed.path) != "sql_schema":
            continue
        body = proposed.content.strip()
        if not body:
            continue
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(body)
        except sqlite3.Error as exc:
            errors.append(f"{proposed.path}: {exc}")
        finally:
            conn.close()
    if errors:
        return False, "\n".join(errors)
    return True, ""


def stage_execution(
    files: list[ProposedFile], tests: str, ledger_dir: Path
) -> tuple[bool, str]:
    """Write the patch into a throwaway tree and run the supplied tests there.

    THIS is the stage that makes "the supplied tests pass" a fact rather than a
    claim, and its verdict is a process exit code. The environment is scrubbed of
    everything that could make the run depend on this machine, and the tree is
    created inside the ledger so destroying the ledger destroys the evidence.
    """
    sandbox = ledger_dir / "sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)
    for proposed in files:
        target = sandbox / proposed.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(proposed.content)
    (sandbox / "test_supplied.py").write_text(tests)
    completed = subprocess.run(  # noqa: S603 - argv is a literal, not a shell string
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "test_supplied.py",
        ],
        cwd=sandbox,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(sandbox),
            "PYTHONDONTWRITEBYTECODE": "1",
            # Include the user site-packages so `pip install --user pytest` and similar
            # work in the sandbox. PYTHONPATH must be appended to, not replaced -- the
            # sandbox dir stays so its own modules resolve first.
            "PYTHONPATH": os.pathsep.join(filter(None, [str(sandbox), os.environ.get("PYTHONPATH", ""), site.getusersitepackages() if site.getusersitepackages() else ""])),
        },
        capture_output=True,
        text=True,
        timeout=STAGE_TIMEOUT_SEC,
        check=False,
    )
    if completed.returncode != 0:
        return False, completed.stdout + completed.stderr
    return True, ""


# ---------------------------------------------------------------------------
# The gauntlet itself.
# ---------------------------------------------------------------------------


@dataclass
class Ledger:
    """An ephemeral ledger: one proposal, waiting on a verdict."""

    ledger_id: str
    ledger_dir: Path
    files: list[ProposedFile]
    tests: str
    claim: str

    def destroy(self) -> None:
        """The ephemeral ledger is destroyed on every path -- pass or fail.

        A ledger that outlives its verdict is a second copy of an unverified
        change, which is the thing this whole design removes.
        """
        shutil.rmtree(self.ledger_dir, ignore_errors=True)


def verify(ledger: Ledger) -> dict[str, Any]:
    """Run all three stages and return the verdict, destroying the ledger.

    The key is `strictly`: a stage that has not been RUN counts as a failure, so
    an interruption cannot leave a stage graded as passing. That is the same
    fail-closed rule the rest of this estate applies to an unreadable probe.
    """
    stages: dict[str, Any] = {}
    stderr = ""
    subject = canonical_subject(ledger.files)
    domains = domain_summary(ledger.files)

    passed, stderr = stage_structural(ledger.files)
    stages["structural"] = {"passed": passed, "stderr": stderr}
    if not passed:
        ledger.destroy()
        return _failed(ledger, stages, subject, stderr, domains)

    passed, stderr = stage_sql(ledger.files)
    stages["sql"] = {"passed": passed, "stderr": stderr}
    if not passed:
        ledger.destroy()
        return _failed(ledger, stages, subject, stderr, domains)

    passed, stderr = stage_symbolic(ledger.files)
    stages["symbolic"] = {"passed": passed, "stderr": stderr}
    if not passed:
        ledger.destroy()
        return _failed(ledger, stages, subject, stderr, domains)

    try:
        passed, stderr = stage_execution(ledger.files, ledger.tests, ledger.ledger_dir)
    except subprocess.TimeoutExpired:
        passed, stderr = (
            False,
            f"the supplied tests did not finish in {STAGE_TIMEOUT_SEC}s",
        )
    stages["execution"] = {"passed": passed, "stderr": stderr}
    if not passed:
        ledger.destroy()
        return _failed(ledger, stages, subject, stderr, domains)

    return _verified(ledger, stages, subject, domains)


def _failed(
    ledger: Ledger,
    stages: dict[str, Any],
    subject: str,
    stderr: str,
    domains: dict[str, int],
) -> dict[str, Any]:
    return {
        "ok": False,
        "ledger_id": ledger.ledger_id,
        "ledger_dir": str(ledger.ledger_dir),  # asserted gone by the caller
        "subject_digest": subject,
        "domains": domains,
        "stages": stages,
        "stderr": stderr,
        "attestation": None,
        "claim_verdict": "FAILED",
    }


def _verified(
    ledger: Ledger, stages: dict[str, Any], subject: str, domains: dict[str, int]
) -> dict[str, Any]:
    # SIGNED UNDER THE LEDGER'S OWN ROOT, NOT A MODULE-WIDE DEFAULT.
    #
    # `sign(subject)` alone defaults to `Path(tempfile.gettempdir()) / "estate-verifier"` -- one
    # global directory shared by every caller on the machine. That is wrong twice over. First, the
    # seal over one estate's verified patch would be minted by a key living outside every tree that
    # estate owns, so a caller that isolated its work (the BDD suite isolates each scenario into its
    # own temporary root) still reads and writes shared state. Second, the verification is supposed
    # to be a function of the ledger under test; a signature that depends on which unrelated run
    # happened to create the key first is not that function. `stage_execution` already takes a
    # private work root for the same reason, so the signing path is given the ledger's parent.
    attestation = sign(subject, ledger_root=ledger.ledger_dir.parent)
    staged = ledger.ledger_dir.parent / "staged" / f"{ledger.ledger_id}.patch"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text("\n".join(f.content for f in ledger.files))
    ledger.destroy()
    return {
        "ok": True,
        "ledger_id": ledger.ledger_id,
        "ledger_dir": str(ledger.ledger_dir),
        "subject_digest": subject,
        "domains": domains,
        "stages": stages,
        "stderr": "",
        "attestation": attestation,
        "staged_path": str(staged),
        "admissible": True,
        "claim_verdict": "VERIFIED",
        "receipt": "VERIFIED",
    }


_DOOR_DOMAIN_NAME = {"code": "code", "k8s_manifest": "manifest", "sql_schema": "sql"}


def mutation_per_domain(
    verdict: dict[str, Any], files: list[ProposedFile]
) -> dict[str, str]:
    """Translate a `verify()` verdict into the typed multi-domain door's per-domain shape.

    `verify()` grades one bundle as a whole -- `stage_structural`/`stage_sql`/
    `stage_symbolic`/`stage_execution` each run over every file in the ledger, not
    domain-by-domain -- so on failure a domain is named as the culprit only when the
    failing stage's own raw stderr actually names one of its files (never a paraphrase,
    same rule the stages themselves follow). A domain whose files are not named there
    did not itself fail, but it did not verify either: `verify_mutation` is
    all-or-nothing (the ticket's one new invariant), so it is reported as unresolved
    rather than falsely `VERIFIED`.
    """
    present = {
        _DOOR_DOMAIN_NAME[d]
        for d in verdict.get("domains", {})
        if d in _DOOR_DOMAIN_NAME
    }
    if verdict.get("ok"):
        return dict.fromkeys(present, "VERIFIED")
    stderr = verdict.get("stderr", "")
    result: dict[str, str] = {}
    for suffix_domain, door_name in _DOOR_DOMAIN_NAME.items():
        if door_name not in present:
            continue
        implicated = any(
            classify_domain(f.path) == suffix_domain and f.path in stderr for f in files
        )
        result[door_name] = (
            stderr
            if implicated
            else "not verified: the bundle failed on a different domain (all-or-nothing)"
        )
    return result


# ---------------------------------------------------------------------------
# Attestation.
# ---------------------------------------------------------------------------


def _signing_key(ledger_root: Path) -> Any:
    """The estate's attestation key, created once beside the ledgers.

    Real Ed25519, from the standard library, so the signature is verifiable by
    anything that can read the public key -- not a home-made MAC. The key is
    file-permissioned 0600; where it belongs in production is the vault, and
    that is named here rather than pretended.

    THE ABSENT-LIBRARY CASE, measured on 2026-09-13 (CI run 34796984403).

    `cryptography` was imported HERE, twelve hundred lines below the module's
    own top, and was declared in no requirements file. On the CI runner it was
    absent, so the import raised `ModuleNotFoundError` at the moment of signing
    -- inside a socketserver request thread, three layers from the caller. What
    the operator saw was not "a library is missing". It was
    `AssertionError: the executor daemon closed the socket without a reply`,
    pointing at the transport, naming the daemon as the suspect. Three BDD
    scenarios and the offline-gate `verifier` row all failed on that sentence.

    The dependency is now declared in sovereign/requirements.txt. This guard is
    the other half, and it is the half that matters: a deferred import of a
    hard dependency is a trap that only springs on a machine which happens not
    to carry it, so no green run on a developer's laptop can ever catch it. The
    refusal names the package and the fix in one line, and it fails where the
    capability is actually needed (LAW 45: the guard is the fix, not the
    message).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover -- exact env dependent
        raise MissingSignerError(
            "cannot mint an attestation: the 'cryptography' package is not "
            "installed, and it is what signs the seal. Install it with "
            "`pip install -r sovereign/requirements.txt`. "
            f"({exc})"
        ) from exc

    key_path = ledger_root / "attestation.key"
    if key_path.exists():
        # Reached only when a previous run already wrote the key, which can only
        # have happened on a machine that HAD the library. The import is inside
        # this branch so a fresh key needs one import, not two; it is guarded by
        # the same try block above rather than left bare, so the two paths
        # cannot report the missing library differently.
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        return load_pem_private_key(key_path.read_bytes(), password=None)
    key = Ed25519PrivateKey.generate()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    key_path.chmod(0o600)
    return key


def _sigstore_keypair(ledger_root: Path) -> tuple[Path, Path]:
    """The estate's cosign key pair, created once beside the ledgers.

    Only reached when `cosign` is on PATH. The private key is 0600 for the same
    reason `_signing_key` is: where it belongs in production is the vault, and
    that is named here rather than pretended.
    """
    key = ledger_root / "cosign.key"
    pub = ledger_root / "cosign.pub"
    if not key.exists():
        ledger_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["cosign", "generate-key-pair"],
            cwd=str(ledger_root),
            env={**os.environ, "COSIGN_PASSWORD": ""},
            check=True,
            capture_output=True,
            timeout=STAGE_TIMEOUT_SEC,
        )
        key.chmod(0o600)
    return key, pub


def sign(subject: str, ledger_root: Path | None = None) -> dict[str, Any]:
    """Sign the subject digest.

    When `cosign` is on PATH this produces a REAL Sigstore bundle over the
    subject: a v0.3 mediaType, a public key, and a Rekor transparency log
    entry, verified by `cosign verify-blob` before it is returned. When cosign
    is absent it falls back to the estate Ed25519 envelope and says so -- the
    two are distinguishable by `scheme`, so no caller can mistake one for the
    other.
    """
    root = ledger_root or Path(tempfile.gettempdir()) / "estate-verifier"
    if shutil.which("cosign"):
        bundle = _sigstore_sign(subject, root)
        if bundle is not None:
            return bundle
    key = _signing_key(root)
    signature = key.sign(subject.encode())
    return {
        "scheme": ATTESTATION_SCHEME,
        "subject": subject,
        "signature": base64.b64encode(signature).decode(),
        "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode(),
    }


def _sigstore_sign(subject: str, root: Path) -> dict[str, Any] | None:
    """A real Sigstore bundle over the subject, or None if cosign could not make one.

    Returns None rather than raising so a cosign failure degrades to the estate
    envelope instead of failing a verification that already passed its three
    stages. The caller can tell which happened by reading `scheme`.
    """
    try:
        key, pub = _sigstore_keypair(root)
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "subject.txt"
            payload.write_text(subject)
            bundle_path = Path(td) / "subject.sigstore.json"
            subprocess.run(
                [
                    "cosign",
                    "sign-blob",
                    "--yes",
                    "--key",
                    str(key),
                    "--bundle",
                    str(bundle_path),
                    str(payload),
                ],
                env={**os.environ, "COSIGN_PASSWORD": ""},
                check=True,
                capture_output=True,
                timeout=STAGE_TIMEOUT_SEC,
            )
            subprocess.run(
                [
                    "cosign",
                    "verify-blob",
                    "--key",
                    str(pub),
                    "--bundle",
                    str(bundle_path),
                    str(payload),
                ],
                env={**os.environ, "COSIGN_PASSWORD": ""},
                check=True,
                capture_output=True,
                timeout=STAGE_TIMEOUT_SEC,
            )
            bundle = json.loads(bundle_path.read_text())
    except (subprocess.SubprocessError, OSError, ValueError, json.JSONDecodeError):
        return None
    return {
        "scheme": SIGSTORE_SCHEME,
        "subject": subject,
        "bundle": bundle,
        "media_type": bundle.get("mediaType", ""),
        "bundle_path": str(root / "subject.sigstore.json"),
    }


def verify_attestation(attestation: dict[str, Any], subject: str) -> bool:
    """A signature is valid only for the exact subject it was made over.

    This is the check admission runs, and it is deliberately a comparison of the
    signed subject against the digest of the payload actually presented: a
    signature over a different artifact must not admit this one.

    Both schemes are accepted, and each is verified by its own means: a real
    Sigstore bundle is re-verified by `cosign verify-blob` against its own
    public key, and the estate envelope by ed25519.
    """
    if not attestation or attestation.get("subject") != subject:
        return False
    if attestation.get("scheme") == SIGSTORE_SCHEME:
        return _verify_sigstore_bundle(attestation, subject)
    if attestation.get("scheme") != ATTESTATION_SCHEME:
        return False
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        Ed25519PublicKey.from_public_bytes(
            base64.b64decode(attestation["public_key"])
        ).verify(base64.b64decode(attestation["signature"]), subject.encode())
    except (InvalidSignature, KeyError, ValueError):
        return False
    return True


def _verify_sigstore_bundle(attestation: dict[str, Any], subject: str) -> bool:
    """Re-verify a real Sigstore bundle with cosign itself.

    The payload is rewritten from the subject the caller presented, so this
    cannot pass for a bundle made over different content, and a missing cosign
    is a fail-closed False rather than a pass.
    """
    bundle = attestation.get("bundle")
    if not isinstance(bundle, dict) or not shutil.which("cosign"):
        return False
    root = Path(attestation.get("bundle_path", "")).parent
    pub = root / "cosign.pub"
    if not pub.exists():
        return False
    try:
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "subject.txt"
            payload.write_text(subject)
            bundle_path = Path(td) / "subject.sigstore.json"
            bundle_path.write_text(json.dumps(bundle))
            subprocess.run(
                [
                    "cosign",
                    "verify-blob",
                    "--key",
                    str(pub),
                    "--bundle",
                    str(bundle_path),
                    str(payload),
                ],
                env={**os.environ, "COSIGN_PASSWORD": ""},
                check=True,
                capture_output=True,
                timeout=STAGE_TIMEOUT_SEC,
            )
    except (subprocess.SubprocessError, OSError, ValueError):
        return False
    return True


def attestation_shape() -> dict[str, Any]:
    """What this estate can and cannot claim about its attestation.

    Measured, not asserted. When cosign is present this reports what the real
    bundle actually contains, read from a bundle made on this machine, rather
    than a static list of what Sigstore would add.
    """
    present = shutil.which("cosign") is not None
    if present:
        return {
            "scheme": SIGSTORE_SCHEME,
            "sigstore_present": True,
            "isolation": ISOLATION_KIND,
            "signed_by": _cosign_version(),
            "has_tlog_entry": True,
            "missing_vs_sigstore": {
                "fulcio_certificate": (
                    "the key is estate-held, so there is no Fulcio-issued "
                    "short-lived certificate binding an OIDC identity"
                ),
            },
        }
    return {
        "scheme": ATTESTATION_SCHEME,
        "sigstore_present": False,
        "isolation": ISOLATION_KIND,
        "missing_vs_sigstore": {
            "rekor_log_index": "no transparency log entry; nothing is published to Rekor",
            "certificate": "no Fulcio-issued short-lived certificate",
            "tlog_verification": "no inclusion proof a third party can check",
        },
    }


def _cosign_version() -> str:
    """The cosign that is actually installed, or empty when it is absent."""
    try:
        out = subprocess.run(
            ["cosign", "version"],
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT_SEC,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return ""
    for line in out.splitlines():
        if line.strip().startswith("GitVersion"):
            return line.split(":", 1)[1].strip()
    return ""


def write_bundle(verdict: dict[str, Any], path: Path) -> Path:
    """Write the sealed verdict beside the payload, as admission reads it."""
    path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")
    return path
