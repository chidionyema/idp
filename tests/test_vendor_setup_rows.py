import base64
import copy
import datetime
import json
import os
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin" / "lib"))

import vendor_setup as vs  # noqa: E402

GOOD = {
    "kind": "secret",
    "page": "https://example.invalid/keys",
    "shape": "tok_[0-9a-f]{32}",
    "store_default": "estate-vault",
    "verify": {
        "method": "GET",
        "url": "https://example.invalid/v",
        "headers": {"Authorization": "Bearer {key}"},
    },
    "targets": [{"ns": "llm", "field": "FAKE_API_KEY"}],
    "setup": {
        "road": "browser",
        "entry": "fake-env",
        "steps": [
            {"goto": "https://example.invalid"},
            {
                "wait": {
                    "role": "button",
                    "name": "(?i)create token",
                    "wait_s": 300,
                    "why": "sign in",
                }
            },
            {"click": {"role": "button", "name": "(?i)create token"}},
            {"fill": {"label": "(?i)token name", "value": "estate-{vendor}-{date}"}},
            {"capture": {"field": "FAKE_API_KEY", "regex": "tok_[0-9a-f]{32}"}},
        ],
    },
}


def test_a_good_row_validates():
    assert vs.validate("fake", GOOD) == []


def _mutate_entry_deleted(row):
    del row["setup"]["entry"]
    return row


def _mutate_ambiguous_step(row):
    row["setup"]["steps"][1] = {
        "wait": {"role": "button", "name": "(?i)create token"},
        "click": {"role": "button", "name": "(?i)create token"},
    }
    return row


def _mutate_capture_field(row):
    row["setup"]["steps"][-1]["capture"]["field"] = "NOT_A_TARGET"
    return row


def _mutate_store_default(row):
    row["store_default"] = "human-vault"
    return row


def _mutate_fill_value(row):
    row["setup"]["steps"][3]["fill"]["value"] = "estate-{vendor}-{secret}"
    return row


def _mutate_road(row):
    row["setup"]["road"] = "magic"
    return row


def _mutate_verify_deleted(row):
    del row["verify"]
    return row


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (_mutate_entry_deleted, "setup.entry is required"),
        (_mutate_ambiguous_step, "exactly one of"),
        (_mutate_capture_field, "is not the field of any target"),
        (_mutate_store_default, "estate-vault"),
        (_mutate_fill_value, "unknown template brace {secret}"),
        (_mutate_road, "is not one of"),
        (_mutate_verify_deleted, "verify: block"),
    ],
)
def test_each_broken_shape_is_refused(mutate, expected):
    row = mutate(copy.deepcopy(GOOD))
    errors = vs.validate("fake", row)
    assert any(expected in e for e in errors), errors


def test_every_real_row_validates():
    data = yaml.safe_load((ROOT / "platform/vendors/consoles.yaml").read_text())
    for name, row in data["vendors"].items():
        assert vs.validate(name, row) == []


def test_render():
    assert (
        vs.render("estate-{vendor}-{date}", "grafana", datetime.date(2026, 9, 27))
        == "estate-grafana-20260927"
    )
    with pytest.raises(vs.SetupError):
        vs.render("x-{nope}", "grafana", datetime.date(2026, 9, 27))
    with pytest.raises(vs.SetupError):
        vs.render("x-}", "grafana", datetime.date(2026, 9, 27))


def test_pattern_folds_inline_ignorecase():
    p = vs.pattern("(?i)create token")
    assert p.flags & re.IGNORECASE
    assert p.pattern == "create token"


def test_check_shapes_names_the_field_never_the_value():
    errs = vs.check_shapes(GOOD, {"FAKE_API_KEY": "wrong-secret-value"})
    assert errs == ["FAKE_API_KEY does not match the registry shape"]
    assert "wrong-secret-value" not in "".join(errs)
    good_value = "tok_" + "a" * 32
    assert vs.check_shapes(GOOD, {"FAKE_API_KEY": good_value}) == []


def test_scrub_removes_value_and_base64():
    v = "tok_" + "a" * 32
    text = f"x {v} y {base64.b64encode(v.encode()).decode()} z"
    out = vs.scrub(text, [v])
    assert v not in out
    assert base64.b64encode(v.encode()).decode() not in out
    assert out.count("<redacted>") == 2


def test_write_vault_keeps_values_off_argv_and_removes_the_file(tmp_path, monkeypatch):
    script = tmp_path / "fake-vault-put"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "env_file = os.environ['ESTATE_ENV_FILE']\n"
        "record = {\n"
        "    'argv': sys.argv[1:],\n"
        "    'env_file': env_file,\n"
        "    'keys': [line.split('=', 1)[0] for line in open(env_file).read().splitlines()],\n"
        "    'mode': oct(os.stat(env_file).st_mode & 0o777),\n"
        "}\n"
        "with open(os.environ['FAKE_VAULT_RECORD'], 'w') as f:\n"
        "    f.write(json.dumps(record))\n"
        "sys.exit(0)\n"
    )
    script.chmod(0o755)

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("IDP_VAULT_PUT", str(script))
    monkeypatch.setenv("FAKE_VAULT_RECORD", str(record_path))

    value = "tok_" + "b" * 32
    vs.write_vault("fake-env", {"FAKE_API_KEY": value}, str(ROOT))

    record = json.loads(record_path.read_text())
    assert record["argv"] == ["--merge", "fake-env", "FAKE_API_KEY=V_FAKE_API_KEY"]
    assert all(value not in item for item in record["argv"])
    assert record["keys"] == ["V_FAKE_API_KEY"]
    assert record["mode"] == "0o600"
    assert not os.path.exists(record["env_file"])


def test_a_refused_vault_write_is_scrubbed(tmp_path, monkeypatch):
    script = tmp_path / "fake-vault-put"
    script.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "env_file = os.environ['ESTATE_ENV_FILE']\n"
        "sys.stderr.write(open(env_file).read())\n"
        "sys.exit(3)\n"
    )
    script.chmod(0o755)

    monkeypatch.setenv("IDP_VAULT_PUT", str(script))

    value = "tok_" + "c" * 32
    with pytest.raises(vs.SetupError) as exc_info:
        vs.write_vault("fake-env", {"FAKE_API_KEY": value}, str(ROOT))

    message = str(exc_info.value)
    assert "exit 3" in message
    assert value not in message
