"""crew#406: both ImageUpdateAutomation objects sat not-ready for days on
`failed to run template from spec: ... can't evaluate field Changes in type []update.Change`.

`.Changed.Objects` is a map from object reference to its list of changes; the old template
ranged the list again with `.Changes`. The controller evaluates the template only at push time,
so the manifest applied clean and the failure lived only in the cluster. The receipt that found
it is `bin/idp-cluster-state` (idp#287). Rung 4, incident test, over every ImageUpdateAutomation
in the repo: the template ranges the map with named bindings and never dots into `.Changes`.
"""
import pathlib
import re

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
AUTOMATIONS = sorted(IDP.glob("platform/image-automation/*.yaml"))


def _templates():
    out = []
    for path in AUTOMATIONS:
        for doc in yaml.safe_load_all(path.read_text()):
            if doc and doc.get("kind") == "ImageUpdateAutomation":
                out.append((path.name, doc["spec"]["git"]["commit"]["messageTemplate"]))
    return out


def template_evaluates(tmpl: str) -> bool:
    if re.search(r"range\s+\.Changes\b", tmpl):
        return False
    return bool(re.search(r"range\s+\$\w+,\s*\$\w+\s*:=\s*\.Changed\.Objects", tmpl))


def test_every_image_update_automation_template_ranges_the_change_map():
    found = _templates()
    assert len(found) >= 1, found          # one automation since crew#406 (shared push branch collided)
    for name, tmpl in found:
        assert template_evaluates(tmpl), f"{name}: {tmpl}"


def test_the_rule_refuses_the_template_that_broke_and_permits_the_fix():
    broke = "{{ range .Changed.Objects }}{{ range .Changes }}{{ .NewValue }}{{ end }}{{ end }}"
    fixed = "{{ range $resource, $changes := .Changed.Objects }}{{ range $_, $change := $changes }}{{ $change.NewValue }}{{ end }}{{ end }}"
    assert not template_evaluates(broke)
    assert template_evaluates(fixed)
