"""The docs named 47 files that exist nowhere in the estate, and nothing had ever checked.

Measured 2026-08-29 across 297 tracked markdown files in `crew` and `idp`: relative markdown
links were clean (0 broken in either repo), but 63 backticked file paths written in prose pointed
at nothing. Most were not typos -- they were cross-repo references written as if the reader were
standing in the other repo (`drills/catalogue.yaml` from crew, meaning `idp/drills/catalogue.yaml`),
so a founder or a buyer's engineer following the sentence lands nowhere and cannot tell whether
the file moved, was deleted, or never existed.

Rung 3, incident test. The trap this closes is that prose is unexecutable: a path in a sentence
is a claim about the repository, and until something reads it back, it decays silently the moment
a file moves. Every other claim in this estate has to carry a receipt; this one did not.

In idp, measured 2026-08-29 against `c1a48505`: 20 mentions in 11 docs, and two of them were
load-bearing rather than cosmetic -- `policy/adapters.rego`, which the laws page's generator
read on every run and which is on no branch of the guards repo, and `backstage/compose.yml`,
which `make catalogue-deploy` still built from and which never landed on main at all.

The ratchet is `ALLOWED` below. A path is allowed only with a reason on the line, and the reason
has to say why the file is legitimately absent -- not "we have not got to it yet". Adding a name
here is a decision someone can read; leaving a dead path in the prose was not.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Every repo in `~/dev/code` a doc may point into. A path starting with one of these names is a
#: cross-repo reference, and CI checks out one repo, so it cannot be resolved here. Repointing the
#: 34 bare paths into this form was most of the fix; a prefix at least tells the reader WHERE.
SIBLINGS = {
    "crew",
    "idp",
    "prospector",
    "prospector-main",
    "hermes-v2",
    "hermes-audit",
    "survival-stack",
    "maestro",
    "agent-guard",
    "ebookStore",
    "ecommerce-clean",
    "QAlgo",
    "mumchimp-medusa",
    "e26-rescue",
    "forex_trend_prediction",
}

#: A backticked token with a slash and a source-file extension. Deliberately narrow: prose is full
#: of bare words in backticks, and grading those would be grading English.
TICK = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|sh|tf|ya?ml|md|rego|json|ts|go))`")

#: Placeholders in templates (`docs/decisions/NNNN-title.md`) name a shape, not a file.
PLACEHOLDER = re.compile(r"NNNN|issue-N\.|<[a-z]+>|\.\.\.")

#: path -> why it is legitimately absent. Read this as a list of things the estate has NOT got.
ALLOWED = {
    "docs/inventory.json": "written by the estate-inventory workflow onto the state/live-diagram branch only "
    "(crew#740); the Ops tile reads it there through the /estate-state proxy, never from main",
    "docs/inventory.md": "the same table as text, on the state/live-diagram branch only (crew#740)",
    "claude-guards/laws/AGENTS.md": "the laws file in the claude-guards repository, which is checked out under the home "
    "directory (not as a sibling of this one); named by the Langfuse incident report",
    ".github/workflows/security-scan.yml": "the copy bin/estate-security-rollout installs in every OTHER repository; idp's own copy "
    "is platform/github/workflows/security-scan.yml, named in the same sentence",
    "docs/configuration/integrations/traefik.md": "upstream oauth2-proxy documentation, read while deciding ADR 0007; not a file here",
    "providers/github.md": "upstream oauth2-proxy documentation, read while deciding ADR 0007; not a file here",
    "catalog/manifests/cp5-caddy.yaml": "the manifest `idp-reconcile --fix` removed; the sentence records the removal, so the "
    "file being absent is the thing it says",
    "scratchpad/phase1.sh": "the scratch script the 2026-08-25 demo transcript was recorded from; never committed",
}


def _tracked_markdown() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.md", "**/*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(set(out.split()))


#: An absolute path is always a defect, and it is the one this guard nearly missed. `ROOT / t` for
#: an absolute `t` is `t` itself, so `/Users/<someone>/dev/code/...` EXISTS on the machine that
#: wrote it and does not exist anywhere else -- the check passed on the laptop and failed on the
#: CI runner (crew#616, run 33228113856). LAW 46: a file never names where the checkout lives.
_ABSOLUTE = (
    "an absolute path names this machine (LAW 46) -- write it relative to the repo, or "
    "prefixed with the sibling repo: `hermes-v2/profiles/architect/MEMORY.md`"
)


_OUTSIDE = (
    "a `../` path escapes the checkout -- write the sibling repo's name instead: "
    "`crew/science/scheduler/estate_dagster/facts.py`, not `../../crew/science/...`"
)


def _escapes(rel: str) -> bool:
    """A path that climbs out of the repo. `git check-ignore` answers it with
    `fatal: ... is outside repository` and exit 128, which reads as "not ignored" -- so the old
    order called it dead for the right reason by accident, after printing a fatal on stderr."""
    return rel.split("/")[0] == ".."


def _is_generated(rel: str) -> bool:
    """A path .gitignore covers is written by a run, so it is absent in a clean checkout and
    present after one. `science/foresight-state.json` is real; refusing it would be a guard that
    refuses correct work (LAW 38)."""
    #: check=False is the point: exit 1 means "not ignored", which is an answer, not a failure.
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "-q", rel], check=False
        ).returncode
        == 0
    )


def dead_paths() -> dict[str, list[str]]:
    """{doc: [paths it names that resolve to nothing]}."""
    dead: dict[str, list[str]] = {}
    for doc in _tracked_markdown():
        p = ROOT / doc
        for m in TICK.finditer(p.read_text(errors="replace")):
            t = m.group(1)
            if "/" not in t or PLACEHOLDER.search(t):
                continue
            if t.startswith(("http", "//")) or "github.com/" in t:
                continue  # a URL that happens to end in .md
            if t.startswith("/"):
                dead.setdefault(doc, []).append(t)  # LAW 46, and see _ABSOLUTE below
                continue
            if t.split("/")[0] in SIBLINGS:
                continue  # another repo; not checked out here
            if _escapes(t):
                dead.setdefault(doc, []).append(t)  # see _OUTSIDE
                continue
            if (ROOT / t).exists() or (p.parent / t).exists():
                continue
            if _is_generated(t):
                continue
            dead.setdefault(doc, []).append(t)
    return dead


def test_no_doc_names_a_file_that_does_not_exist():
    unexplained = {
        doc: [t for t in ts if t not in ALLOWED] for doc, ts in dead_paths().items()
    }
    unexplained = {d: ts for d, ts in unexplained.items() if ts}
    assert not unexplained, (
        f"these docs name paths that resolve to nothing ({_ABSOLUTE}; {_OUTSIDE}). Repoint the path (a cross-repo reference "
        "needs its repo prefix: `idp/drills/catalogue.yaml`, not `drills/catalogue.yaml`), delete "
        "the sentence, or add the path to ALLOWED with the reason it is legitimately absent:\n"
        + "\n".join(f"  {d}: {', '.join(ts)}" for d, ts in sorted(unexplained.items()))
    )


def test_no_doc_names_an_absolute_path():
    """Graded separately because it is the case that got through.

    A relative dead path fails everywhere. An absolute one passes on the machine that wrote it --
    `ROOT / "/Users/x/..."` is `/Users/x/...`, which exists there -- and fails only on a runner.
    crew#616 run 33228113856 caught four of them in AGENT-ONBOARDING.md after the local run said
    4 passed. This assertion holds on the laptop too.
    """
    absolute = {
        doc: [t for t in ts if t.startswith("/")] for doc, ts in dead_paths().items()
    }
    absolute = {d: ts for d, ts in absolute.items() if ts}
    assert not absolute, f"{_ABSOLUTE}\n" + "\n".join(
        f"  {d}: {', '.join(ts)}" for d, ts in sorted(absolute.items())
    )


def test_the_allowlist_does_not_outlive_the_paths_it_excuses():
    """An excuse for a path nobody names any more is dead weight that hides the next one."""
    named = {t for ts in dead_paths().values() for t in ts}
    stale = sorted(set(ALLOWED) - named)
    assert not stale, (
        "ALLOWED still excuses paths no doc names. Delete these entries:\n  "
        + "\n  ".join(stale)
    )


def test_every_excuse_says_why_the_file_is_absent():
    thin = sorted(k for k, v in ALLOWED.items() if len(v) < 25)
    assert not thin, (
        f"an entry with no real reason is not a decision anyone can review: {thin}"
    )


def test_a_cross_repo_path_is_recognised_by_its_prefix():
    """The fix's whole shape in one assertion: the prefix is what makes the sentence followable."""
    assert (
        "idp" in SIBLINGS and "hermes-v2" in SIBLINGS and "survival-stack" in SIBLINGS
    )
    assert "drills/catalogue.yaml".split("/")[0] not in SIBLINGS
    assert "idp/drills/catalogue.yaml".split("/")[0] in SIBLINGS


def test_a_path_that_escapes_the_checkout_is_classified_before_git_sees_it():
    """Found in the idp run of this guard, which printed
    `fatal: ../../crew/science/scheduler/estate_dagster/facts.py: ... is outside repository`
    from inside check-ignore. The verdict was right and the route to it was not: exit 128 is an
    error, and reading it as "not ignored" is the silent-green shape (LAW 8, fix it where found).
    """
    assert _escapes("../../crew/science/scheduler/estate_dagster/facts.py")
    assert not _escapes("crew/science/scheduler/estate_dagster/facts.py")
    assert not _escapes("scheduler/estate_scheduler/describe.py")
