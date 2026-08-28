"""bin/idp-kyverno-render judged every render against the sibling checkout and never this repo.

2026-08-28. Three ClusterPolicies live in this repository and are reconciled onto the cluster by
clusters/oke -- platform/edge/kyverno-secrets-policy.yaml, platform/scheduling/capacity-affinity
.yaml, platform/scheduling/require-priority-class.yaml. The pre-merge judge resolved its policy
set from $IDP_KYVERNO_POLICIES or prospector's deploy/k8s/policies and never looked here, so
those three were applied to no render, ever: a rule that could refuse a Deployment at admission
after the merge and had no way to refuse it before.

Same class as crew#539, closed one file up the same script: there the estate-only policies lived
in a checkout CI did not have and the verdict said "render clean" against 24 of 26 policies while
the cluster refused robusta on the 25th, and monitoring stayed down 8h. crew#539's fix named the
two missing policies in a list. A list is the part that does not survive the next policy, so this
one derives: the loader walks platform/ and these tests walk platform/, and neither knows a name.
"""
import os
import subprocess
import sys

import yaml

IDP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(IDP, "platform")
LOADER = os.path.join(IDP, "bin", "idp-kyverno-own-policies")
RENDER = os.path.join(IDP, "bin", "idp-kyverno-render")


def shipped_policies():
    """Every ClusterPolicy under platform/, found the way an operator would: by reading them."""
    found = {}
    for dirpath, _, names in os.walk(PLATFORM):
        for n in names:
            if not n.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(dirpath, n)
            try:
                docs = list(yaml.safe_load_all(open(path)))
            except (yaml.YAMLError, UnicodeDecodeError):
                continue
            for d in docs:
                if isinstance(d, dict) and d.get("kind") == "ClusterPolicy":
                    found[d["metadata"]["name"]] = os.path.relpath(path, IDP)
    return found


def test_this_repo_ships_cluster_policies_at_all():
    """The premise. If it ever goes to zero the tests below pass vacuously and prove nothing."""
    shipped = shipped_policies()
    assert shipped, "no ClusterPolicy under platform/: the tests below would pass on an empty set"


def test_every_policy_this_repo_ships_reaches_the_judged_set(tmp_path):
    empty = tmp_path / "policies.yaml"
    empty.write_text("")
    out = subprocess.run([sys.executable, LOADER, PLATFORM, str(empty)],
                         capture_output=True, text=True, check=True).stdout
    loaded = {d["metadata"]["name"] for d in yaml.safe_load_all(empty.read_text())
              if isinstance(d, dict) and d.get("kind") == "ClusterPolicy"}
    shipped = shipped_policies()
    missing = {n: p for n, p in shipped.items() if n not in loaded}
    assert not missing, (
        f"the judge would render against a set that omits {missing}; that is the 2026-08-28 "
        f"blindness back. Loader said: {out.strip()!r}")


def test_a_policy_already_in_the_rendered_set_is_not_duplicated(tmp_path):
    """The sibling set and this repo both carry secrets-not-from-env-vars today. Kyverno reports
    one verdict per policy name per resource; two copies would double every count in the render
    line and make a fail look like two fails."""
    shipped = shipped_policies()
    name = sorted(shipped)[0]
    doc = None
    for dirpath, _, names in os.walk(PLATFORM):
        for n in names:
            if os.path.relpath(os.path.join(dirpath, n), IDP) == shipped[name]:
                doc = [d for d in yaml.safe_load_all(open(os.path.join(dirpath, n)))
                       if isinstance(d, dict) and d.get("kind") == "ClusterPolicy"
                       and d["metadata"]["name"] == name][0]
    pre = tmp_path / "policies.yaml"
    pre.write_text(yaml.safe_dump(doc, sort_keys=False))
    subprocess.run([sys.executable, LOADER, PLATFORM, str(pre)],
                   capture_output=True, text=True, check=True)
    names = [d["metadata"]["name"] for d in yaml.safe_load_all(pre.read_text())
             if isinstance(d, dict) and d.get("kind") == "ClusterPolicy"]
    assert names.count(name) == 1, f"{name} was written twice: {names}"


def test_a_file_the_loader_cannot_parse_is_skipped_not_fatal(tmp_path):
    """platform/ holds Helm values and chart templates. A judge that dies on one of them is a
    judge nobody runs, and the fallback that gets reached for is `|| true`."""
    root = tmp_path / "platform"
    (root / "chart").mkdir(parents=True)
    (root / "chart" / "template.yaml").write_text("{{- if .Values.x }}\nkind: NotYaml: [\n")
    (root / "real.yaml").write_text(
        "apiVersion: kyverno.io/v1\nkind: ClusterPolicy\nmetadata:\n  name: a-real-one\nspec: {}\n")
    out = tmp_path / "policies.yaml"
    out.write_text("")
    r = subprocess.run([sys.executable, LOADER, str(root), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "a-real-one" in out.read_text(), "the unparseable neighbour swallowed a real policy"


def test_the_render_script_loads_them_before_it_judges_anything():
    """The loader existing is not the fix; being called is. It must run before the first
    `kyverno apply`, or the first render is judged against the set that was missing them."""
    body = open(RENDER).read()
    call = body.index("idp-kyverno-own-policies")
    apply_at = body.index("kyverno apply")
    assert call < apply_at, "the own policies are loaded after the first render is judged"
    assert '"$IDP/bin/idp-kyverno-own-policies"' in body, (
        "the loader is invoked by a relative path: the judge is run from CI, from a worktree and "
        "from a pre-push hook, and only $IDP is true in all three (LAW 46)")
