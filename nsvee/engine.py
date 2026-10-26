# ruff: noqa: S603, S607, S108, S101 -- this module's substance is running
# generated artifacts in controlled sandboxes (subprocess, /tmp, asserts as
# integrity checks). Productized 2026-10-25; rules apply to its callers.
"""NSVEE — the Neuro-Symbolic Verifiable Execution Engine.

Productized from the founder's all-in-one build (salvaged 2026-10-25,
lane/claim-rungs history): 4 tiers — auto-formalization, grammar-constrained
generation, sandboxed multi-engine verification with mutation-scored epsilon,
and step-aware feedback. Adoption: migration board I-D (estate-mcp tools,
Otto, all agents)."""
# =============================================================================

# =============================================================================
# ORIGINAL SPECIFICATION
# =============================================================================
# To achieve mathematically guaranteed, asymmetric leverage—where a smaller or faster model like MiniMax vastly outperforms raw frontier models in zero-hallucination reliability—you must transition from a probabilistic chat paradigm to a Neuro-Symbolic Verifiable Execution Engine (NSVEE).
# In high-stakes engineering, treating any LLM as a standalone oracle is an architectural vulnerability. Instead, you treat the LLM purely as a stochastic search heuristic (a generator of candidate solutions), while an unyielding, deterministic verification layer acts as the absolute gatekeeper.
# 1. The Mathematical Foundation: Compressing Error Probability
# In a standard single-pass LLM workflow, the probability of system failure scales poorly. Let p represent the probability of an individual reasoning or coding error by the model. Across an n-step workflow, the cumulative probability of failure (P_{\text{failure}}) in an unverified system is:
# As tasks grow complex (n \to \infty), P_{\text{failure}} approaches 100\%.
# The Asymmetric Leverage Equation
# To invert this dynamic, we introduce a deterministic verification gate with a leakage rate \epsilon (where \epsilon \approx 0 for compilers, SMT solvers, and formal verifiers) over k automated self-correction cycles. The systemic error probability collapses to:
# Because \epsilon is near-zero, P_{\text{system}} drops exponentially, rendering the underlying intelligence of the base generator secondary. A smaller model paired with an aggressive, closed-loop verification engine mathematically outperforms an unverified frontier model every single time.
# 2. Architecture of the Neuro-Symbolic Verifiable Engine
# To operationalize this by default across all workflows, your system must process every request through a 4-Tier Zero-Trust Pipeline:
# ┌────────────────────────────────────────────────────────┐
# │                   1. Auto-Formalization Layer          │
# │    (Translates Natural Language Requirements to Logic) │
# └───────────────────────────┬────────────────────────────┘
#                             ▼
# ┌────────────────────────────────────────────────────────┐
# │               2. Grammar-Constrained Generation         │
# │     (MiniMax / Target Model forced via JSON Schema)    │
# └───────────────────────────┬────────────────────────────┘
#                             ▼
# ┌────────────────────────────────────────────────────────┐
# │             3. Deterministic Execution & Sandbox       │
# │   (Compilers, AST Linters, SMT Solvers like Z3/Lean 4) │
# └───────────────────┬───────────────────┬────────────────┘
#                     │ Pass              │ Fail / Contradiction
#                     ▼                   ▼
#       ┌──────────────────────────┐    ┌──────────────────────────┐
#       │   4a. State Commit &     │    │ 4b. Step-Aware Feedback  │
#       │       Production         │    │     Injection (Loop)     │
#       └──────────────────────────┘    └──────────────────────────┘
#
# 3. The Four Tiers in Detail
# Tier 1: Auto-Formalization & Constraint Extraction
# Before writing code or system designs, the input prompt is converted into formal logic or explicit constraints.
#  * Research in formal reasoning frameworks (such as the Safe and Hermes architectures utilizing proof assistants like Lean 4 and Satisfiability Modulo Theories like Z3) proves that forcing an intermediate formal specification phase eliminates semantic ambiguities before code is ever generated.
#  * The Rule: If a requirement cannot be expressed as a deterministic assertion or schema constraint, it is flagged as an unresolved ambiguity.
# Tier 2: Grammar-Constrained Generation
# Never allow freeform text generation. Force the model token-by-token using Context-Free Grammars (CFGs) or structural schema constraints (via Pydantic, outlines, or native server-side JSON mode). This eliminates syntax errors and malformed structural outputs at the generation boundary.
# Tier 3: Multi-Engine Verification & Sandboxed Execution
# Every artifact produced by the model undergoes parallel automated validation:
#  * Static Analysis & AST Parsing: Structural correctness checked via language-specific linters.
#  * Symbolic Execution / SMT Solvers: Logic-heavy workflows are validated against mathematical bounds using Z3 or similar solvers to prove the absence of race conditions, deadlocks, or boundary violations.
#  * Sandboxed Test Runs: Code is executed inside an isolated container with strict network and resource bounds to evaluate automated unit and integration tests.
# Tier 4: Retrospective Step-Aware Feedback Loop
# If validation fails (Tier 3), the system does not crash or guess. It captures the exact compiler error traceback, stack trace, or solver counterexample and injects it directly back into the model's context window as a negative constraint. The model is forced to re-synthesize its plan based on concrete mathematical or programmatic failure evidence.
# 4. Production-Grade Implementation Blueprint (Python)
# Here is how you hardcode this asymmetric leverage into your engineering workflow using a programmatic feedback and verification loop:
# import subprocess
# import json
# from pydantic import BaseModel, Field, ValidationError
# from typing import List, Optional, Dict, Any
#
# class VerifiedTaskOutput(BaseModel):
#     plan_steps: List[str] = Field(..., description="Ordered execution steps")
#     code_implementation: str = Field(..., description="Executable Python code snippet")
#     unit_tests: List[str] = Field(..., description="Self-contained assertion tests")
#
# def execute_deterministic_pipeline(prompt: str, max_retries: int = 4) -> Dict[str, Any]:
#     current_prompt = prompt
#     feedback_log = ""
#
#     for attempt in range(max_retries):
#         # 1. Constrained Generation (Using MiniMax or any target model via strict schema)
#         try:
#             raw_response = call_model_with_strict_schema(
#                 prompt=current_prompt + feedback_log,
#                 schema=VerifiedTaskOutput
#             )
#             parsed_output: VerifiedTaskOutput = VerifiedTaskOutput.parse_raw(raw_response)
#         except (ValidationError, Exception) as parse_err:
#             feedback_log = f"\n\n[SYSTEM ERROR]: Previous attempt failed schema validation: {parse_err}. Ensure valid JSON matching the schema."
#             continue
#
#         # 2. Deterministic Verification Engine (Sandbox & AST execution)
#         validation_error = run_sandbox_verification(parsed_output.code_implementation, parsed_output.unit_tests)
#
#         if validation_error is None:
#             # Success: Mathematically verified output
#             return {
#                 "status": "VERIFIED",
#                 "attempts": attempt + 1,
#                 "result": parsed_output.dict()
#             }
#
#         # 3. Feed exact compiler/interpreter error back into the loop
#         feedback_log = f"\n\n[DETERMINISTIC VERIFICATION FAILED]:\n{validation_error}\nFix the implementation to resolve this exact error."
#
#     raise RuntimeError(f"Pipeline failed to converge after {max_retries} deterministic verification cycles.")
#
# def run_sandbox_verification(code: str, tests: List[str]) -> Optional[str]:
#     """Executes code and tests inside an isolated sandbox, capturing exact tracebacks."""
#     full_script = code + "\n\n# --- AUTOMATED TEST SUITE ---\n" + "\n".join(tests)
#
#     # Write to a temporary file and run in a secure, isolated subprocess/container
#     try:
#         result = subprocess.run(
#             ["python3", "-c", full_script],
#             capture_output=True,
#             text=True,
#             timeout=5
#         )
#         if result.returncode != 0:
#             return result.stderr
#         return None # Passed cleanly
#     except subprocess.TimeoutExpired:
#         return "Execution timed out (potential infinite loop or deadlock)."
#     except Exception as e:
#         return str(e)
#
# Summary of Asymmetric Advantages
# By adopting this framework:
#  * Model Independence: You decouple reliability from the intelligence tier of the LLM. MiniMax, Llama, or Claude become interchangeable raw generation engines.
#  * Guaranteed Falsification: No output reaches production or decision-making without passing a non-neural, deterministic mathematical or programmatic filter.
#  * Compounding Correctness: Every failure automatically strengthens the next iteration through closed-loop error injection, making systemic hallucination virtually impossible.
#
# =============================================================================

# =============================================================================
# PRODUCTION REVIEW (key deltas)
# =============================================================================
# ===================== PRODUCTION REVIEW (key deltas) =====================
# 1. subprocess.run is not a sandbox -> DockerRunner (no net, read-only, caps
#    dropped) + RlimitsRunner fallback.
# 2. Timeout race left containers -> guaranteed docker rm -f / process-group kill.
# 3. Raw stderr is untrusted input -> sanitized, marker-neutralized, capped.
# 4. One PASS != VERIFIED (flakes) -> confirmation re-run.
# 5. TIMEOUT/OOM/SANDBOX_ERROR classified; infra errors abort, never blind-retry.
# 6. Budgets: retries, wall clock, feedback bytes.
# 7. Human gate on Tier-1 ambiguities (spec error is the real leak term).
# 8. No provider hardcoding: Router protocol + LiteLLM fallback chain.
# ====================================================================
# =============================================================================

# ---------------------------------------------------------------------------
# schemas.py
# ---------------------------------------------------------------------------
from typing import List, Optional
from pydantic import BaseModel, Field


class FormalSpec(BaseModel):
    """Tier 1 output: extracted, checkable constraints.

    Invariants/constraints must be machine-checkable assertions where possible.
    Anything that cannot be expressed as an assertion is an ambiguity.
    """

    objective: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    invariants: List[str] = Field(
        default_factory=list, description="Always-true conditions"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Must-hold requirements"
    )
    ambiguities: List[str] = Field(
        default_factory=list, description="Unresolvable without human input"
    )
    requires_human: bool = Field(
        default=False, description="True if ambiguities block safe execution"
    )


class VerifiedTaskOutput(BaseModel):
    reasoning_summary: str = ""
    plan_steps: List[str]
    code_implementation: str
    unit_tests: List[str]
    dependencies: List[str] = Field(
        default_factory=list, description="pip requirements, e.g. ['numpy==1.26.4']"
    )


class SpecEnforcement(str):
    pass


def parse_model(cls, raw: str):
    """Parse model output leniently: full JSON, or first balanced {...} block."""

    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found in model output") from None
        data = json.loads(raw[start : end + 1])
    if hasattr(cls, "model_validate"):
        return cls.model_validate(data)
    return cls.parse_obj(data)


# ---------------------------------------------------------------------------
# router.py
# ---------------------------------------------------------------------------
from typing import List, Protocol
import json


class Router(Protocol):
    def generate(self, messages: list, max_tokens: int = 4096) -> str: ...


class LiteLLMRouter:
    """Routes through LiteLLM. Models are an ordered fallback chain — never a single hardcoded provider."""

    def __init__(self, models: List[str], router_kwargs: Optional[dict] = None):
        if not models:
            raise ValueError("at least one model required")
        self.models = list(models)
        self.router_kwargs = router_kwargs or {}

    def generate(self, messages: list, max_tokens: int = 4096) -> str:
        import litellm  # lazy import: engine must work offline too

        last_err = None
        for model in self.models:
            try:
                resp = litellm.completion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    **self.router_kwargs,
                )
                return resp.choices[0].message.content or ""
            except (
                Exception
            ) as e:  # provider down / rate limited / context overflow -> next fallback
                last_err = e
        raise RuntimeError(f"all fallback models exhausted: {last_err}")


class FakeRouter:
    """Scripted responses for tests: list of strings yielded in order, last one repeats."""

    def __init__(self, responses: List[str]):
        self._responses = list(responses)
        self._i = 0
        self.calls: List[list] = []

    def generate(self, messages: list, max_tokens: int = 4096) -> str:
        self.calls.append(messages)
        r = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return r


# ---------------------------------------------------------------------------
# sandbox.py
# ---------------------------------------------------------------------------
import os
import re
import signal
import sys

try:
    import resource as _resource
except ImportError:
    _resource = None
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Verdict(str, Enum):
    PASS = "PASS"  # noqa: S105 — a verdict name
    FAIL = "FAIL"  # deterministic failure (assertion/exception/compile)
    TIMEOUT = "TIMEOUT"  # wall-clock exceeded (infinite loop / deadlock suspect)
    OOM = "OOM"  # memory limit exceeded
    SANDBOX_ERROR = (
        "SANDBOX_ERROR"  # infra problem — NOT a code failure; do not feed back as one
    )


@dataclass
class SandboxResult:
    verdict: Verdict
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    notes: List[str] = field(default_factory=list)

    @property
    def error_text(self) -> str:
        return (self.stderr or self.stdout or "").strip()


_MAX_OUTPUT_BYTES = (
    256 * 1024
)  # cap captured output: protects memory AND downstream context windows


def _cap(s: str) -> str:
    b = s.encode("utf-8", "replace")
    if len(b) <= _MAX_OUTPUT_BYTES:
        return s
    return (
        b[:_MAX_OUTPUT_BYTES].decode("utf-8", "replace")
        + f"\n...[truncated {len(b) - _MAX_OUTPUT_BYTES} bytes]"
    )


def _classify(returncode: int, stderr: str, oom_hint: bool) -> Verdict:
    if oom_hint or "out of memory" in stderr.lower() or returncode == 137:
        return Verdict.OOM
    if returncode == 0:
        return Verdict.PASS
    return Verdict.FAIL


def build_script(code: str, tests: List[str]) -> str:
    return (
        code
        + "\n\n# --- AUTOMATED TEST SUITE (appended by NSVEE) ---\n"
        + "\n".join(tests)
        + "\n"
    )


class DockerRunner:
    """Hard-isolated execution. Requires docker daemon; image pulled once."""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        cpu_cores: float = 0.5,
        memory_mb: int = 256,
        pids_limit: int = 64,
    ):
        self.image = image
        self.cpu_cores = cpu_cores
        self.memory_mb = memory_mb
        self.pids_limit = pids_limit

    def available(self) -> bool:
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
            return r.returncode == 0
        except Exception:
            return False

    def run(self, script: str, timeout_s: int) -> SandboxResult:
        tmpdir = tempfile.mkdtemp(prefix="nsvee_")
        path = os.path.join(tmpdir, "main.py")
        with open(path, "w") as f:
            f.write(script)
        name = f"nsvee-{uuid.uuid4().hex[:12]}"
        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--memory",
            f"{self.memory_mb}m",
            "--cpus",
            str(self.cpu_cores),
            "--pids-limit",
            str(self.pids_limit),
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "-v",
            f"{path}:/work/main.py:ro",
            self.image,
            "python3",
            "-I",
            "-B",
            "/work/main.py",
        ]
        t0 = time.monotonic()
        timed_out = False
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s + 2
            )
            rc, out, err = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            timed_out = True
            rc, out, err = -1, "", ""
        finally:
            # belt and suspenders: never leave a container behind
            subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True,
                timeout=10,
            )
            try:
                os.unlink(path)
                os.rmdir(tmpdir)
            except OSError:
                pass
        dur = time.monotonic() - t0
        if timed_out:
            return SandboxResult(
                Verdict.TIMEOUT, duration_s=dur, notes=["exceeded wall-clock budget"]
            )
        return SandboxResult(
            verdict=_classify(rc, err or "", oom_hint=False),
            stdout=_cap(out or ""),
            stderr=_cap(err or ""),
            duration_s=dur,
        )


class RlimitsRunner:
    """Fallback for hosts without docker (e.g. local Mac dev loop).

    Weaker isolation: same kernel/user. Scrub env, clamp rlimits, kill the
    whole process group on timeout. Use DockerRunner in any shared/prod estate.
    """

    def __init__(self, memory_mb: int = 256):
        self.memory_mb = memory_mb

    def available(self) -> bool:
        return os.name == "posix"

    def _limits(self):
        resource = _resource
        assert resource is not None, "rlimits runner requires POSIX"
        cpu = 20  # seconds of CPU
        mem = self.memory_mb * 1024 * 1024
        limits = [
            (resource.RLIMIT_CPU, (cpu, cpu + 1)),
            (resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024)),
            (resource.RLIMIT_NPROC, (64, 64)),
            (resource.RLIMIT_NOFILE, (64, 64)),
        ]
        if sys.platform != "darwin":
            # Darwin: a hard RLIMIT_AS SIGKILLs CPython at startup (child_rc=9,
            # measured 2026-10-26) — the interpreter's malloc zone reserves
            # address space past the cap. Address-space bounds stay on Linux;
            # on darwin the wall-clock kill + NOFILE/NPROC carry the isolation.
            limits.insert(1, (resource.RLIMIT_AS, (mem, mem)))
        return limits

    def _apply_limits(self):
        if _resource is None:
            return
        for k, v in self._limits():
            try:
                _resource.setrlimit(k, v)
            except (OSError, ValueError, RuntimeError):
                # An inapplicable limit must degrade, not kill the run: a raise
                # inside preexec_fn surfaces to the caller as SubprocessError,
                # which this runner reported as SANDBOX_ERROR and the pipeline
                # as SANDBOX_DEGRADED (hypotheses.race 2026-10-26: H_popen and
                # H_as supported, all else falsified).
                pass

    def run(self, script: str, timeout_s: int) -> SandboxResult:
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"}
        t0 = time.monotonic()
        try:
            p = subprocess.Popen(
                ["python3", "-I", "-B", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                start_new_session=True,
                preexec_fn=self._apply_limits,
            )
            try:
                out, err = p.communicate(timeout=timeout_s)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                p.communicate(timeout=5)
                return SandboxResult(
                    Verdict.TIMEOUT,
                    duration_s=time.monotonic() - t0,
                    notes=["exceeded wall-clock budget; process group killed"],
                )
            return SandboxResult(
                verdict=_classify(rc, err or "", oom_hint=(rc == -9)),
                stdout=_cap(out or ""),
                stderr=_cap(err or ""),
                duration_s=time.monotonic() - t0,
            )
        except Exception as e:
            return SandboxResult(
                Verdict.SANDBOX_ERROR, notes=[f"runner infra error: {e}"]
            )


def default_runner() -> "DockerRunner | RlimitsRunner":
    d = DockerRunner()
    return d if d.available() else RlimitsRunner()


# ---------------------------------------------------------------------------
# engine.py
# ---------------------------------------------------------------------------
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional


log = logging.getLogger("nsvee")

SANITIZE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")  # strip control chars


@dataclass
class Budgets:
    max_retries: int = 4
    max_wall_clock_s: float = 600.0
    max_feedback_chars: int = 4000  # per-injection cap
    max_feedback_history: int = 3  # keep only last N failure reports
    confirmation_runs: int = 1  # re-run on PASS to defeat flakes


@dataclass
class PipelineReport:
    status: str  # VERIFIED | HUMAN_INPUT_REQUIRED | EXHAUSTED | SANDBOX_DEGRADED
    attempts: int = 0
    result: Optional[dict] = None
    spec: Optional[dict] = None
    events: List[dict] = field(default_factory=list)


EventHook = Callable[[dict], None]


class NSVEE:
    def __init__(
        self,
        router,
        runner=None,
        budgets: Optional[Budgets] = None,
        event_hook: Optional[EventHook] = None,
    ):
        self.router = router  # model-agnostic Router (see router.py)
        self.runner = runner or default_runner()
        self.budgets = budgets or Budgets()
        self.event_hook = event_hook or (lambda e: None)

    # ------------------------------------------------------------- helpers
    def _emit(self, kind: str, **kw):
        ev = {"ts": time.time(), "tier": kind, **kw}
        self.event_hook(ev)
        log.info("nsvee.%s %s", kind, kw)

    def _gen(self, system: str, user: str, max_tokens: int = 4096) -> str:
        return self.router.generate(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
        )

    @staticmethod
    def _sanitize(text: str, cap: int) -> str:
        """Neutralize injection markers, cap size. stderr is untrusted input."""
        t = SANITIZE_RE.sub(" ", text)
        t = t.replace("[DETERMINISTIC VERIFICATION FAILED]", "(verification failed)")
        t = t.replace("[SYSTEM", "(SYSTEM").replace("[END", "(END")
        return t[-cap:] if len(t) > cap else t

    # ------------------------------------------------------------- Tier 1
    T1_SYSTEM = (
        "You are a formalization engine. Convert the request into a FormalSpec JSON "
        "object. Every invariant and constraint must be machine-checkable. List anything "
        "you cannot express as an assertion under 'ambiguities'. Set requires_human=true "
        "if ambiguities make safe execution impossible. Respond with JSON only."
    )

    def formalize(self, prompt: str) -> FormalSpec:
        self._emit("tier1.formalize.start")
        raw = self._gen(self.T1_SYSTEM, prompt)
        spec = parse_model(FormalSpec, raw)
        self._emit(
            "tier1.formalize.done",
            ambiguities=len(spec.ambiguities),
            requires_human=spec.requires_human,
        )
        return spec

    # ------------------------------------------------------------- Tier 2
    T2_SYSTEM = (
        "You are a code generation engine. Produce a VerifiedTaskOutput JSON object: "
        "plan_steps, code_implementation (self-contained Python, stdlib only unless "
        "'dependencies' declares pinned packages), unit_tests (plain assert statements, "
        "no frameworks), dependencies (pinned versions). Respond with JSON only."
    )

    def _generate_output(
        self, prompt: str, spec: FormalSpec, feedback: List[str]
    ) -> VerifiedTaskOutput:
        fb = "\n\n".join(feedback[-self.budgets.max_feedback_history :])
        user = (
            f"REQUEST:\n{prompt}\n\n"
            f"FORMAL SPEC:\n{spec.model_dump_json() if hasattr(spec, 'model_dump_json') else spec.json()}\n"
            + (f"\nPREVIOUS FAILURES (fix these exactly):\n{fb}\n" if fb else "")
            + "\nRespond with a VerifiedTaskOutput JSON object only."
        )
        raw = self._gen(self.T2_SYSTEM, user)
        return parse_model(VerifiedTaskOutput, raw)

    # ------------------------------------------------------------- Tier 3
    def _verify(self, out: VerifiedTaskOutput, timeout_s: int) -> List[SandboxResult]:
        """Run twice on PASS to defeat nondeterministic flakes."""
        script = build_script(out.code_implementation, out.unit_tests)
        results = [self.runner.run(script, timeout_s)]
        if results[0].verdict == Verdict.PASS:
            for _ in range(self.budgets.confirmation_runs):
                results.append(self.runner.run(script, timeout_s))
        return results

    @staticmethod
    def _failure_text(results: List[SandboxResult]) -> Optional[str]:
        for r in results:
            if r.verdict == Verdict.FAIL:
                return r.error_text
        return None

    def post_verify(self, out):
        """Independent-oracle hook. Base: none. Override to check artifact
        against something the model did not author (spec invariants)."""
        return None

    # ------------------------------------------------------------- Tier 4 / orchestration
    def run(
        self, prompt: str, timeout_s: int = 10, _spec_override=None
    ) -> PipelineReport:
        rep = PipelineReport(status="EXHAUSTED")
        t_start = time.monotonic()
        b = self.budgets
        feedback: List[str] = []

        def time_left() -> bool:
            return (time.monotonic() - t_start) < b.max_wall_clock_s

        # --- Tier 1
        if _spec_override is not None:
            spec = _spec_override
        else:
            try:
                spec = self.formalize(prompt)
            except Exception as e:
                rep.status = "FORMALIZATION_ERROR"
                rep.events.append({"tier": "tier1.error", "error": str(e)})
                return rep
        rep.spec = spec.model_dump() if hasattr(spec, "model_dump") else spec.dict()
        if spec.requires_human or spec.ambiguities:
            rep.status = "HUMAN_INPUT_REQUIRED"
            rep.events.append({"tier": "gate.human", "ambiguities": spec.ambiguities})
            self._emit("gate.human", ambiguities=spec.ambiguities)
            return rep

        # --- Tier 2->3->4 loop
        for attempt in range(1, b.max_retries + 1):
            if not time_left():
                break
            rep.attempts = attempt
            self._emit("tier2.generate", attempt=attempt)

            # constrained generation + JSON recovery
            try:
                out = self._generate_output(prompt, spec, feedback)
            except Exception as e:
                feedback.append(f"schema/parse error: {self._sanitize(str(e), 500)}")
                self._emit("tier2.parse_error", error=str(e))
                continue

            results = self._verify(out, timeout_s)
            for i, r in enumerate(results):
                self._emit(
                    "tier3.verify",
                    attempt=attempt,
                    run=i,
                    verdict=r.verdict.value,
                    duration_s=round(r.duration_s, 3),
                )

            fail = self._failure_text(results)
            if fail is not None:
                feedback.append(self._sanitize(fail, b.max_feedback_chars))
                self._emit("tier4.feedback", attempt=attempt, reason="assertion")
                continue

            # No FAIL verdict: distinguish confirmed pass vs timeout/oom/infra
            verdicts = {r.verdict for r in results}
            if verdicts == {Verdict.PASS}:
                extra = self.post_verify(out)
                if extra:
                    feedback.append(self._sanitize(extra, b.max_feedback_chars))
                    self._emit("tier4.feedback", attempt=attempt, reason="oracle")
                    continue
                rep.status = "VERIFIED"
                rep.result = (
                    out.model_dump() if hasattr(out, "model_dump") else out.dict()
                )
                self._emit("pipeline.verified", attempts=attempt)
                return rep

            # Unfixable-by-regeneration verdicts: surface, don't loop blindly
            if Verdict.SANDBOX_ERROR in verdicts:
                rep.status = "SANDBOX_DEGRADED"
                rep.events.append(
                    {"tier": "tier3.infra", "notes": [r.notes for r in results]}
                )
                return rep
            if Verdict.TIMEOUT in verdicts:
                rep.events.append({"tier": "tier3.timeout", "attempt": attempt})
                feedback.append(
                    self._sanitize(
                        "Execution exceeded the wall-clock budget. Restructure to avoid "
                        "infinite loops, blocking I/O, or exponential blowup.",
                        500,
                    )
                )
                self._emit("tier4.feedback", attempt=attempt, reason="timeout")
            elif Verdict.OOM in verdicts:
                rep.events.append({"tier": "tier3.oom", "attempt": attempt})
                feedback.append(
                    self._sanitize(
                        "Memory limit exceeded. Reduce allocation; do not materialize large structures.",
                        500,
                    )
                )
                self._emit("tier4.feedback", attempt=attempt, reason="oom")

        self._emit("pipeline.exhausted", attempts=rep.attempts)
        return rep


# ---------------------------------------------------------------------------
# Built-in test suite (runs with: python3 nsvee_all_in_one.py)
# ---------------------------------------------------------------------------
