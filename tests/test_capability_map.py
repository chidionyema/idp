"""The estate map: one pass over everything the estate has, and the places it contends.

Each test carries the case that must trip the detector and the case it must leave alone,
because a conflict finder that cannot be wrong in either direction is not a gate.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

DOOR = Path(__file__).resolve().parent.parent / "bin" / "capability-index"


@pytest.fixture(scope="module")
def ci():
    loader = importlib.machinery.SourceFileLoader("capability_index_map", str(DOOR))
    spec = importlib.util.spec_from_loader("capability_index_map", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def rec(cap_id, kind="tool", plane="idp", summary="", path="", depends=(), state=None):
    health = {"state": state} if state else {}
    return {
        "id": cap_id,
        "kind": kind,
        "plane": plane,
        "summary": summary,
        "path": path,
        "depends_on": list(depends),
        "contract": {"inputs": [], "outputs": ["stdout"], "errors": ["non-zero exit"]},
        "health": health,
    }


def classes(ci, records):
    return sorted(c["class"] for c in ci.find_conflicts(records))


def test_one_name_two_kinds_is_a_name_conflict(ci):
    found = ci.find_conflicts(
        [rec("cap:intent/build-image", "intent"), rec("cap:tool/build-image", "tool")]
    )
    assert [c["class"] for c in found] == ["NAME"]
    assert found[0]["ids"] == ["cap:intent/build-image", "cap:tool/build-image"]


def test_same_leaf_in_different_service_namespaces_is_not_a_conflict(ci):
    records = [
        rec("cap:service/acg/redis", "service"),
        rec("cap:service/otto/redis", "service"),
    ]
    assert ci.find_conflicts(records) == []


def test_identical_prose_in_one_kind_is_a_twin(ci):
    text = "the budget governor ends a reasoning loop before it burns the budget"
    found = ci.find_conflicts(
        [
            rec("cap:tool/idp-budget", summary=text),
            rec("cap:tool/budget.py", summary=text),
        ]
    )
    assert [c["class"] for c in found] == ["TWIN"]


@pytest.mark.parametrize(
    "text",
    [
        "use anyhow::{anyhow, result};",
        "<!doctype html><meta charset=utf-8>",
        "short label",
    ],
)
def test_a_scraped_source_line_or_a_label_is_not_a_twin(ci, text):
    records = [rec("cap:tool/a", summary=text), rec("cap:tool/b", summary=text)]
    assert ci.find_conflicts(records) == []


def test_a_description_shared_by_a_template_sized_group_is_not_a_twin(ci):
    text = "loaded, plist in no repository, so nobody owns it"
    records = [rec(f"cap:workflow/w{i}", "workflow", summary=text) for i in range(10)]
    assert ci.find_conflicts(records) == []
    assert classes(ci, records[:9]) == ["TWIN"]


def test_one_file_claimed_by_two_kinds_is_shared_but_one_manifest_of_services_is_not(
    ci,
):
    two_kinds = [
        rec("cap:tool/x", "tool", path="bin/x"),
        rec("cap:intent/y", "intent", path="bin/x"),
    ]
    assert classes(ci, two_kinds) == ["SHARED"]
    one_manifest = [
        rec("cap:service/acg/gateway", "service", path="platform/acg/workload.yaml"),
        rec("cap:service/acg/redis", "service", path="platform/acg/workload.yaml"),
    ]
    assert ci.find_conflicts(one_manifest) == []


def test_a_dependency_on_a_record_that_does_not_exist_is_dangling(ci):
    found = ci.find_conflicts(
        [
            rec("cap:tool/a", depends=["cap:tool/b"]),
            rec("cap:tool/c", depends=["cap:tool/a"]),
        ]
    )
    assert [(c["class"], c["ids"]) for c in found] == [
        ("DANGLING", ["cap:tool/a", "cap:tool/b"])
    ]


def test_a_clean_registry_has_no_findings(ci):
    clean = [
        rec(
            "cap:intent/one",
            "intent",
            summary="reads the thing and reports the first line",
        ),
        rec("cap:tool/two", summary="writes a different thing to a different place"),
    ]
    assert ci.find_conflicts(clean) == []
    assert ci.estate_map(clean, "snapshot")["conflicts"]["total"] == 0


def test_the_map_counts_what_is_proven_and_what_is_only_declared(ci, monkeypatch):
    monkeypatch.setattr(
        ci, "read_record", lambda r: r
    )  # health derivation has its own tests
    records = [
        rec("cap:tool/a", plane="idp", state="operating"),
        rec("cap:tool/b", plane="idp"),
        rec("cap:intent/c", "intent", plane="estate", state="degraded"),
    ]
    m = ci.estate_map(records, "store")
    assert m["records"] == 3 and m["source"] == "store"
    assert m["states"]["operating"] == 1 and m["states"]["degraded"] == 1
    assert m["states"]["declared"] == 1
    assert m["planes"]["idp"]["operating"] == 1 and m["planes"]["idp"]["declared"] == 1
    assert m["proven_share"] == pytest.approx(1 / 3, abs=1e-4)


def test_templated_contracts_are_counted_not_credited(ci):
    records = [rec(f"cap:tool/t{i}") for i in range(ci.TEMPLATE_MIN)]
    records.append(
        {
            **rec("cap:tool/own"),
            "contract": {"inputs": ["a"], "outputs": ["b"], "errors": []},
        }
    )
    assert ci.estate_map(records, "snapshot")["templated_contracts"] == ci.TEMPLATE_MIN


def test_the_founder_view_fits_one_telegram_message_even_with_a_thousand_conflicts(ci):
    records = [rec(f"cap:tool/n{i}", "tool", path=f"p{i}") for i in range(1000)] + [
        rec(f"cap:intent/n{i}", "intent", path=f"p{i}") for i in range(1000)
    ]
    view = ci.estate_map(records, "store")
    assert view["conflicts"]["total"] >= 1000
    text = ci.render_map(view, limit=6, telegram=True)
    assert len(text) < 3500
    assert "declared-only" in text and "Declared is not operating" in text
    assert "more: capability-index map --json" in text


def test_the_map_subcommand_is_registered(ci, capsys):
    with pytest.raises(SystemExit) as stop:
        ci.main(["map", "--help"])
    assert stop.value.code == 0
    assert "--telegram" in capsys.readouterr().out


def test_a_record_cannot_claim_operating_without_a_receipt(ci):
    """The map reads health the way every other door does: derived, never self-declared."""
    claimed = [rec("cap:tool/a", state="operating")]
    assert ci.estate_map(claimed, "store")["states"]["operating"] == 0
