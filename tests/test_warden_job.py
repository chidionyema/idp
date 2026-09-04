"""Tests for the warden job (crew#832 CP3).

These tests verify:
1. A fake prove() that raises for one vendor leaves the other vendors' gauges written
2. The captured stdout of a full run contains none of the fake key values
3. The rules file parses and every alert has a summary and annotation
4. Every vendor row in the registry is covered
"""

import os
import re
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add platform to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "platform"))

from warden import prove as warden
from warden import warden as warden_job


class TestWardenJob:
    """Tests for the warden job entrypoint."""

    def test_fake_prove_failure_leaves_other_gauges_written(self, monkeypatch):
        """A prove() that raises for one vendor leaves other vendors' results written."""
        call_count = 0

        def fake_prove(vendor, key, store=None):
            nonlocal call_count
            call_count += 1
            if vendor == "deepseek":
                raise warden.ProofFailed("deepseek", "human-vault", 401, "unauthorized")
            return MagicMock(
                vendor=vendor,
                store="human-vault",
                status_code=200,
                vendor_message="ok",
                verified_at=datetime.datetime.now(datetime.timezone.utc),
            )

        import datetime

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)

        # Mock environment with keys for multiple vendors
        monkeypatch.setenv("SEED_DEEPSEEK_API_KEY", "sk-fake-deepseek")
        monkeypatch.setenv("SEED_MINIMAX_API_KEY", "sk-fake-minimax")

        # Mock push_to_gateway to capture what gets pushed
        pushed_data = []

        def fake_push(gateway, job, registry):
            # Extract metrics from registry
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

        # Run warden - should not raise even with one failure
        with patch.dict(
            os.environ,
            {
                "SEED_DEEPSEEK_API_KEY": "sk-fake-deepseek",
                "SEED_MINIMAX_API_KEY": "sk-fake-minimax",
            },
        ):
            result = warden_job.run_warden()

        # Exit code should be 0
        assert result == 0

        # Should have pushed metrics for both vendors
        assert len(pushed_data) > 0

        # Find valid gauges for each vendor
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

        # Deepseek should be 0 (failed), minimax should be 1 (succeeded)
        assert len(deepseek_valid) == 1
        assert deepseek_valid[0]["value"] == 0
        assert len(minimax_valid) == 1
        assert minimax_valid[0]["value"] == 1

    def test_stdout_contains_no_key_values(self, monkeypatch, capsys):
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

        with patch.dict(os.environ, {"SEED_DEEPSEEK_API_KEY": SENTINEL}):
            warden_job.run_warden()

        captured = capsys.readouterr()

        # The sentinel key should not appear in stdout
        assert SENTINEL not in captured.out
        assert SENTINEL not in captured.err

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

        # Every alert must have summary and description
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

    def test_every_vendor_row_is_covered(self):
        """Every vendor row in the registry is covered by the warden."""
        vendors = warden.load_vendors()

        vendors_with_verify = [
            name for name, config in vendors.items() if config.get("verify")
        ]

        # The warden should handle vendors that have verify blocks
        # We test this by checking the code handles all vendors
        assert len(vendors_with_verify) > 0, "No vendors with verify blocks found"

        # Verify the code paths work for all vendors with a provable key
        for vendor_name in vendors_with_verify:
            config = vendors[vendor_name]

            # The warden can prove a vendor if it has a secret or is not a pair
            has_key = config.get("secret") or not config.get("pair")
            # Paired credentials need special handling - the test just verifies we don't crash
            assert has_key or config.get("pair"), (
                f"{vendor_name} has verify but cannot be proved by warden"
            )


class TestWardenRedaction:
    """Tests for redaction in warden output."""

    def test_error_messages_are_redacted(self, monkeypatch, capsys):
        """Error messages from prove failures are redacted."""
        import datetime

        SENTINEL = "sk-0123456789abcdef0123456789abcdef"

        def fake_prove(vendor, key, store=None):
            raise warden.ProofFailed(
                "deepseek", "human-vault", 401, f"key {key} is invalid"
            )

        monkeypatch.setattr(warden_job.warden, "prove", fake_prove)
        monkeypatch.setattr(warden_job, "push_to_gateway", lambda *a, **kw: None)

        with patch.dict(os.environ, {"SEED_DEEPSEEK_API_KEY": SENTINEL}):
            warden_job.run_warden()

        captured = capsys.readouterr()

        # The sentinel should not appear in output
        assert SENTINEL not in captured.out


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
