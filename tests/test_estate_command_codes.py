"""CC1 falsifiers: exact grammar, recursive obligation, capacity and fake proof."""
import unittest
from sovereign import command_codes as cc


def cmd(**updates):
    fields = dict(
        ACT="REPAIR", TARGET="legion:8018", EFFECT="PATCH", WORK="4000",
        RESERVE="1200", PROTO="I10+I2", CLASS="provider-capacity",
        PARENT="INS-8018", MODE="ELITE"
    )
    fields.update(updates)
    return "CC1 " + " ".join(k + "=" + v for k, v in fields.items())


class CommandContractTests(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(cc.compile_code(cmd()), cc.compile_code(cmd()))
        self.assertEqual(cc.compile_code(cmd())["signed_by"], "UNKNOWN")

    def test_order_independence(self):
        v = cmd()
        reversed_command = "CC1 " + " ".join(reversed(v.split()[1:]))
        self.assertEqual(
            cc.compile_code(v)["digest_sha256"],
            cc.compile_code(reversed_command)["digest_sha256"]
        )

    def test_mode_cannot_authorize(self):
        value = cc.compile_code(cmd(MODE="GOD", EFFECT="PRIVILEGED"))
        self.assertEqual(value["state"], "COMPILED_NOT_AUTHORIZED")

    def test_duplicate_refused(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code(cmd() + " EFFECT=READ")

    def test_unknown_version_refused(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code("CC2 " + cmd()[4:])

    def test_missing_field_refused(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code("CC1 ACT=OBSERVE")

    def test_injection_refused(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code(cmd(TARGET="$(touch /tmp/exploit)"))

    def test_read_only_observation(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code(cmd(ACT="OBSERVE", EFFECT="PRIVILEGED"))

    def test_protocol_correction_needs_parent(self):
        with self.assertRaises(cc.CommandError):
            cc.compile_code(
                "CC1 ACT=CORRECT_PROTOCOL TARGET=protocol:I10 "
                "EFFECT=PATCH WORK=10 RESERVE=1 PROTO=I10"
            )

    def test_protocol_correction_carries_parent(self):
        self.assertEqual(
            cc.compile_code(cmd(ACT="CORRECT_PROTOCOL"))["parent_obligation"],
            "INS-8018"
        )

    def test_missing_observation_blocks(self):
        self.assertEqual(
            cc.preflight(cc.compile_code(cmd()), None, now_epoch=1000)["verdict"],
            "BLOCKED"
        )

    def test_forged_signed_field_blocks(self):
        obs = dict(
            observed_at_epoch=1000, provider_remaining_tokens=10000,
            account_remaining_tokens=10000, rate_limited=False, signed=True
        )
        self.assertEqual(
            cc.preflight(cc.compile_code(cmd()), obs, now_epoch=1000)["verdict"],
            "BLOCKED"
        )

    def test_stale_offer_blocks(self):
        obs = dict(
            observed_at_epoch=1, provider_remaining_tokens=10000,
            account_remaining_tokens=10000, rate_limited=False
        )
        result = cc.preflight(
            cc.compile_code(cmd()), obs, now_epoch=1000,
            authority_oracle=lambda _: True, observation_oracle=lambda _: True
        )
        self.assertIn("CAPACITY_STALE", result["reasons"])

    def test_recovery_reserve_is_not_spendable(self):
        obs = dict(
            observed_at_epoch=1000, provider_remaining_tokens=5000,
            account_remaining_tokens=10000, rate_limited=False
        )
        result = cc.preflight(
            cc.compile_code(cmd()), obs, now_epoch=1000,
            authority_oracle=lambda _: True, observation_oracle=lambda _: True
        )
        self.assertIn("INSUFFICIENT_HEADROOM", result["reasons"])

    def test_test_oracle_never_grants_effect(self):
        obs = dict(
            observed_at_epoch=1000, provider_remaining_tokens=10000,
            account_remaining_tokens=10000, rate_limited=False
        )
        result = cc.preflight(
            cc.compile_code(cmd()), obs, now_epoch=1000,
            authority_oracle=lambda _: True, observation_oracle=lambda _: True
        )
        self.assertEqual(result["verdict"], "PREFLIGHT_ELIGIBLE_NOT_AUTHORIZED")
        self.assertFalse(result["effect_authorized"])

    def test_rate_limited_offer_denied(self):
        obs = dict(
            observed_at_epoch=1000, provider_remaining_tokens=10000,
            account_remaining_tokens=10000, rate_limited=True
        )
        result = cc.preflight(
            cc.compile_code(cmd()), obs, now_epoch=1000,
            authority_oracle=lambda _: True, observation_oracle=lambda _: True
        )
        self.assertIn("PROVIDER_RATE_LIMIT_UNKNOWN_OR_ACTIVE", result["reasons"])

    def test_malformed_budget_denied(self):
        obs = dict(
            observed_at_epoch="1000", provider_remaining_tokens=10000,
            account_remaining_tokens=10000, rate_limited=False
        )
        result = cc.preflight(
            cc.compile_code(cmd()), obs, now_epoch=1000,
            authority_oracle=lambda _: True, observation_oracle=lambda _: True
        )
        self.assertIn("CAPACITY_MALFORMED", result["reasons"])


if __name__ == "__main__":
    unittest.main()
