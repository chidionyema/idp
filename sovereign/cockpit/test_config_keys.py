"""Unit tests for sovereign.cockpit.config_keys (cp22).

Run:  sovereign/.venv/bin/python -m unittest sovereign.cockpit.test_config_keys -v
"""
from __future__ import annotations

import os
import types
import unittest

from sovereign.cockpit import config_keys


class ResolveTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("COCKPIT_POLL_S", None)

    def test_default_used_when_nothing_set(self):
        self.assertEqual(config_keys.resolve("cockpit.poll_s"), 3)

    def test_env_overrides_default(self):
        os.environ["COCKPIT_POLL_S"] = "9"
        self.assertEqual(config_keys.resolve("cockpit.poll_s"), 9)

    def test_config_module_overrides_env(self):
        os.environ["COCKPIT_POLL_S"] = "9"
        fake_config = types.SimpleNamespace(COCKPIT_POLL_S=42)
        self.assertEqual(config_keys.resolve("cockpit.poll_s", fake_config), 42)

    def test_type_coercion_from_string(self):
        fake_config = types.SimpleNamespace(COCKPIT_PORT="9999")
        self.assertEqual(config_keys.resolve("cockpit.port", fake_config), 9999)
        self.assertIsInstance(config_keys.resolve("cockpit.port", fake_config), int)


class NonSecretDictTests(unittest.TestCase):
    def test_no_key_is_secret_shaped(self):
        # cp22: "no secret value is printed; keys ending in TOKEN, KEY, SECRET
        # show set/unset" -- true here only because none of these keys ever
        # hold one. Asserted, not assumed.
        for key in config_keys.COCKPIT_KEYS:
            self.assertFalse(key.upper().endswith(("TOKEN", "KEY", "SECRET")))

    def test_returns_every_key(self):
        got = config_keys.non_secret_dict()
        self.assertEqual(set(got), set(config_keys.COCKPIT_KEYS))


if __name__ == "__main__":
    unittest.main()
