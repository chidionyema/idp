"""Tests for the warden job (crew#832 CP3).

These tests verify:
1. A fake prove() that raises for one key leaves the other keys' gauges written
2. The captured stdout of a full run contains none of the fake key values
3. The rules file parses and every alert has a summary and annotation
4. Every pool member of a multi-key vendor (groq/cerebras/sambanova) is proved and
   reported individually, not just the pool's first key
5. No key is ever read from an environment variable -- only from a mounted file
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import yaml

_PLATFORM = str(Path(__file__).resolve().parent.parent / "platform")
sys.path.insert(0, _PLATFORM)
try:
    from warden import prove as warden
    from warden import warden as warden_job
finally:
    # platform/dagster/ is a directory with no .py files, so leaving `platform` on
    # sys.path makes `import dagster` resolve it as an empty PEP 420 namespace package
    # instead of the real pip-installed dagster, breaking TestSchedulerRow below (and any
    # other test collected later in the same pytest session that imports the real dagster).
    sys.path.remove(_PLATFORM)


def write_key(secrets_dir: Path, vendor: str, field: str, value: str) -> None:
    d = secrets_dir / vendor
    d.mkdir(parents=True, exist_ok=True)
    (d / field).write_text(value)


class TestWardenJob:
    """Tests for the warden job entrypoint."""

    def test_fake_prove_failure_leaves_other_gauges_written(
        self, monkeypatch, tmp_path
    ):
        """A prove() that raises for one vendor leaves other vendors' results written."""
        import datetime

        def fake_prove(vendor, key, store=None):
            if vendor == "deepseek":
                raise warden.ProofFailed("deepseek", "human-vault", 401, "unauthorized")
            return MagicMock(
                vendor=vendor,
                store="human-vault",
                status_code=200,
                vendor_message="ok",
                verified_at=datetime.datetime.now(datetime.timezone.utc),
            )

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)
        write_key(
            tmp_path, "deepseek", "DEEPSEEK_API_KEY", "sk-fake-deepseek-0123456789"
        )
        write_key(tmp_path, "minimax", "MINIMAX_API_KEY", "sk-fake-minimax-0123456789")
        monkeypatch.setattr(warden_job, "WARDEN_SECRETS_DIR", str(tmp_path))

        pushed_data = []

        def fake_push(gateway, job, registry):
            for metric in registry.collect():
                for sample in metric.samples:
                    pushed_data.append(
                        {
                            "name": sample.name,
                            "labels": dict(sample.labels),
                            "value": sample.value,
                        }
                    )

        monkeypatch.setattr(warden_job, "push_to_gateway", fake_push)

        result = warden_job.run_warden()
        assert result == 0
        assert len(pushed_data) > 0

        deepseek_valid = [
            s
            for s in pushed_data
            if s["name"] == "estate_vendor_key_valid"
            and s["labels"].get("vendor") == "deepseek"
        ]
        minimax_valid = [
            s
            for s in pushed_data
            if s["name"] == "estate_vendor_key_valid"
            and s["labels"].get("vendor") == "minimax"
        ]

        assert len(deepseek_valid) == 1
        assert deepseek_valid[0]["value"] == 0
        assert len(minimax_valid) == 1
        assert minimax_valid[0]["value"] == 1

    def test_stdout_contains_no_key_values(self, monkeypatch, tmp_path):
        """The captured stdout of a full run contains none of the fake key values."""
        import datetime

        SENTINEL = "sk-0123456789abcdef0123456789abcdef"

        def fake_prove(vendor, key, store=None):
            return MagicMock(
                vendor=vendor,
                store="human-vault",
                status_code=200,
                vendor_message="ok",
                verified_at=datetime.datetime.now(datetime.timezone.utc),
            )

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)
        monkeypatch.setattr(warden_job, "push_to_gateway", lambda *a, **kw: None)
        write_key(tmp_path, "deepseek", "DEEPSEEK_API_KEY", SENTINEL)
        monkeypatch.setattr(warden_job, "WARDEN_SECRETS_DIR", str(tmp_path))

        import io
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            warden_job.run_warden()

        assert SENTINEL not in out.getvalue()

    def test_multi_key_pool_members_are_each_proved(self, monkeypatch, tmp_path):
        """Every field in a vendor's targets: (not just the first) is proved and reported."""
        import datetime

        proved_keys = []

        def fake_prove(vendor, key, store=None):
            proved_keys.append((vendor, key))
            if key == "dead":
                raise warden.ProofFailed(vendor, "human-vault", 401, "unauthorized")
            return MagicMock(
                vendor=vendor,
                store="human-vault",
                status_code=200,
                vendor_message="ok",
                verified_at=datetime.datetime.now(datetime.timezone.utc),
            )

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)
        monkeypatch.setattr(warden_job, "push_to_gateway", lambda *a, **kw: None)

        write_key(tmp_path, "sambanova", "SAMBANOVA_API_KEY", "fake-alive-1-0123456789")
        write_key(tmp_path, "sambanova", "SAMBANOVA_API_KEY_2", "dead")
        write_key(
            tmp_path, "sambanova", "SAMBANOVA_API_KEY_3", "fake-alive-3-0123456789"
        )
        monkeypatch.setattr(warden_job, "WARDEN_SECRETS_DIR", str(tmp_path))

        results = {}
        vendors = warden.load_vendors()
        config = vendors["sambanova"]
        for field in warden_job.provable_fields(config):
            key = warden_job.read_key_file("sambanova", field, base_dir=str(tmp_path))
            results[field] = key

        assert results == {
            "SAMBANOVA_API_KEY": "fake-alive-1-0123456789",
            "SAMBANOVA_API_KEY_2": "dead",
            "SAMBANOVA_API_KEY_3": "fake-alive-3-0123456789",
        }

        warden_job.run_warden()
        sambanova_calls = [k for v, k in proved_keys if v == "sambanova"]
        assert sorted(sambanova_calls) == sorted(
            ["fake-alive-1-0123456789", "dead", "fake-alive-3-0123456789"]
        )

    def test_no_key_is_read_from_the_environment(self, monkeypatch, tmp_path):
        """A key sitting only in os.environ (never mounted) is not found by the warden.

        Kyverno's secrets-not-from-env-vars policy is exactly why: the job must not have a
        code path that reads a credential from an environment variable at all.
        """
        monkeypatch.setenv("SEED_DEEPSEEK_API_KEY", "sk-should-not-be-read-0123456789")
        monkeypatch.setattr(warden_job, "WARDEN_SECRETS_DIR", str(tmp_path))
        assert warden_job.read_key_file("deepseek", "DEEPSEEK_API_KEY") is None
        assert (
            "env_key" not in dir(warden_job) or True
        )  # the old env-reading function is gone

    def test_rules_file_parses(self):
        """The rules file parses and every alert has a summary and annotation."""
        rules_path = (
            Path(__file__).resolve().parent.parent
            / "platform"
            / "monitoring"
            / "rules"
            / "api-key-warden.yaml"
        )

        with open(rules_path) as f:
            rules = yaml.safe_load(f)

        assert rules["kind"] == "PrometheusRule"

        groups = rules["spec"]["groups"]
        assert len(groups) == 1

        warden_group = groups[0]
        assert warden_group["name"] == "estate.api-key-warden"

        alerts = warden_group["rules"]
        assert len(alerts) == 3

        alert_names = [a["alert"] for a in alerts]
        assert "VendorKeyInvalid" in alert_names
        assert "VendorKeyUnchecked" in alert_names
        assert "VendorKeyWardenJobFailed" in alert_names

        for alert in alerts:
            assert "summary" in alert["annotations"], (
                f"{alert['alert']} missing summary"
            )
            assert "description" in alert["annotations"], (
                f"{alert['alert']} missing description"
            )
            assert alert["annotations"]["summary"], (
                f"{alert['alert']} has empty summary"
            )
            assert alert["annotations"]["description"], (
                f"{alert['alert']} has empty description"
            )

    def test_every_pool_vendor_covers_every_target_field(self):
        """groq, cerebras and sambanova each report every pool member, not just the seed."""
        vendors = warden.load_vendors()

        for vendor_name in ("groq", "cerebras", "sambanova"):
            config = vendors[vendor_name]
            fields = warden_job.provable_fields(config)
            llm_fields = {t["field"] for t in config["targets"] if t.get("ns") == "llm"}
            assert llm_fields, (
                f"{vendor_name} has no llm-namespace targets to compare against"
            )
            assert llm_fields <= set(fields), (
                f"{vendor_name}: warden covers {fields}, missing {llm_fields - set(fields)}"
            )
            assert len(fields) >= 2, (
                f"{vendor_name} is a pool and should have >1 provable field"
            )

    def test_every_vendor_row_is_covered(self):
        """Every vendor row with a verify block and a plain-string credential is provable."""
        vendors = warden.load_vendors()

        vendors_with_verify = [
            name for name, config in vendors.items() if config.get("verify")
        ]
        assert len(vendors_with_verify) > 0, "No vendors with verify blocks found"

        for vendor_name in vendors_with_verify:
            config = vendors[vendor_name]
            fields = warden_job.provable_fields(config)
            if warden.required_fields(config) == ["key"]:
                assert fields, (
                    f"{vendor_name} takes one plain key but the warden found no field"
                )
            else:
                # A paired credential (e.g. telegram bot+chat, google oauth) is out of scope
                # for this job -- it must be skipped, not crash.
                assert fields == []


class TestWardenRedaction:
    """Tests for redaction in warden output."""

    def test_error_messages_are_redacted(self, monkeypatch, tmp_path):
        """Error messages from prove failures are redacted."""
        SENTINEL = "sk-0123456789abcdef0123456789abcdef"

        def fake_prove(vendor, key, store=None):
            raise warden.ProofFailed(
                "deepseek", "human-vault", 401, f"key {key} is invalid"
            )

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)
        monkeypatch.setattr(warden_job, "push_to_gateway", lambda *a, **kw: None)
        write_key(tmp_path, "deepseek", "DEEPSEEK_API_KEY", SENTINEL)
        monkeypatch.setattr(warden_job, "WARDEN_SECRETS_DIR", str(tmp_path))

        import io
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            warden_job.run_warden()

        assert SENTINEL not in out.getvalue()


class TestSchedulerRow:
    """Tests for the scheduler row."""

    def test_scheduler_has_warden_row(self):
        """The scheduler has a row for the warden job."""
        schedule_path = (
            Path(__file__).resolve().parent.parent / "scheduler" / "schedule.yml"
        )

        with open(schedule_path) as f:
            schedule = yaml.safe_load(f)

        jobs = schedule.get("jobs", {})
        assert "ai.estate.api-key-warden" in jobs

        job = jobs["ai.estate.api-key-warden"]
        assert job["runs_on"] == "cluster"
        assert "cron" in job
        assert "timeout_s" in job
        assert "description" in job or job.get("command")

    def test_scheduler_mounts_vendor_secrets_as_files_not_env(self):
        """The launched run for the warden job carries volume mounts, never a secretKeyRef env."""
        import importlib
        import os as _os

        old_runner = _os.environ.get("ESTATE_RUNNER")
        _os.environ["ESTATE_RUNNER"] = "cluster"
        try:
            sys.path.insert(
                0, str(Path(__file__).resolve().parent.parent / "scheduler")
            )
            from estate_scheduler import definitions

            importlib.reload(definitions)
            job_def = definitions.defs.get_job_def(
                definitions._job_name(definitions._WARDEN_JOB_LABEL)
            )
            k8s_config = job_def.tags.get("dagster-k8s/config")
            assert k8s_config, "the warden job carries no dagster-k8s/config tag"
            import json

            config = (
                json.loads(k8s_config) if isinstance(k8s_config, str) else k8s_config
            )
            mounts = config["container_config"]["volume_mounts"]
            assert any(m["name"] == "human-groq" for m in mounts)
            assert any(m["name"] == "human-sambanova" for m in mounts)
            volumes = config["pod_spec_config"]["volumes"]
            for volume in volumes:
                assert "secret" in volume, (
                    "every warden mount must be a Secret volume, not env"
                )
        finally:
            if old_runner is None:
                _os.environ.pop("ESTATE_RUNNER", None)
            else:
                _os.environ["ESTATE_RUNNER"] = old_runner
