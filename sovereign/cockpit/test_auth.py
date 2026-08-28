"""Unit tests for sovereign.cockpit.auth. stdlib unittest only (CONTRACT.md
"Deps: ... Nothing else" -- no pytest in sovereign/requirements.txt).

Run:  sovereign/.venv/bin/python -m unittest sovereign.cockpit.test_auth -v
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import unittest
from unittest import mock
from urllib.parse import urlencode

from sovereign.cockpit import auth

DUMMY_TOKEN = "123456:AA_dummy_test_token_never_real"
ALLOWED_ID = "555111"


def build_init_data(token: str, user: dict, *, auth_date: int | None = None,
                     extra: dict | None = None, bad_hash: bool = False) -> str:
    """Build a syntactically valid Telegram Mini App initData string signed
    with `token`, per https://core.telegram.org/bots/webapps#validating-data-
    received-via-the-mini-app -- mirrors what auth.verify_init_data checks."""
    fields = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAtest",
    }
    if extra:
        fields.update(extra)
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if bad_hash:
        digest = "0" * len(digest)
    fields["hash"] = digest
    return urlencode(fields)


class VerifyInitDataTests(unittest.TestCase):
    def setUp(self):
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = ALLOWED_ID

    def tearDown(self):
        os.environ.pop("TELEGRAM_ALLOWED_USER_IDS", None)
        os.environ.pop("TELEGRAM_ALLOWED_USERS", None)

    def test_valid_init_data_allow_listed_user_passes(self):
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID), "first_name": "Founder"})
        user = auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)
        self.assertEqual(user["id"], int(ALLOWED_ID))

    def test_valid_init_data_not_allow_listed_rejected(self):
        init_data = build_init_data(DUMMY_TOKEN, {"id": 999999, "first_name": "Stranger"})
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)

    def test_tampered_hash_rejected(self):
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)}, bad_hash=True)
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)

    def test_wrong_signing_token_rejected(self):
        init_data = build_init_data("other:token", {"id": int(ALLOWED_ID)})
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)

    def test_empty_init_data_rejected(self):
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data("", bot_token=DUMMY_TOKEN)

    def test_stale_auth_date_rejected(self):
        stale = int(time.time()) - 999999999  # far older than any reasonable max_age
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)}, auth_date=stale)
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)

    def test_fresh_auth_date_accepted(self):
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)}, auth_date=int(time.time()))
        user = auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)
        self.assertEqual(user["id"], int(ALLOWED_ID))

    def test_no_allow_list_fails_closed(self):
        os.environ.pop("TELEGRAM_ALLOWED_USER_IDS", None)
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)})
        with self.assertRaises(auth.AuthError):
            auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)

    def test_telegram_allowed_users_alias_accepted(self):
        os.environ.pop("TELEGRAM_ALLOWED_USER_IDS", None)
        os.environ["TELEGRAM_ALLOWED_USERS"] = ALLOWED_ID
        init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)})
        user = auth.verify_init_data(init_data, bot_token=DUMMY_TOKEN)
        self.assertEqual(user["id"], int(ALLOWED_ID))


class LoopbackTests(unittest.TestCase):
    def test_ipv4_loopback_true(self):
        self.assertTrue(auth.is_loopback("127.0.0.1"))

    def test_ipv6_loopback_true(self):
        self.assertTrue(auth.is_loopback("::1"))

    def test_lan_address_false(self):
        self.assertFalse(auth.is_loopback("192.168.1.20"))

    def test_garbage_address_false(self):
        self.assertFalse(auth.is_loopback("not-an-ip"))


class AuthorizeTests(unittest.TestCase):
    def setUp(self):
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = ALLOWED_ID

    def tearDown(self):
        os.environ.pop("TELEGRAM_ALLOWED_USER_IDS", None)

    def test_no_init_data_from_loopback_allowed(self):
        self.assertIsNone(auth.authorize(None, "127.0.0.1"))

    def test_no_init_data_not_loopback_rejected(self):
        with self.assertRaises(auth.AuthError):
            auth.authorize(None, "203.0.113.5")

    def test_bad_init_data_from_loopback_still_rejected(self):
        # A present-but-invalid header is always checked, even from loopback --
        # this is the exact case DoD item 4 asks for: bad header, loopback, 401.
        with self.assertRaises(auth.AuthError):
            auth.authorize("garbage=not-signed&hash=deadbeef", "127.0.0.1")

    def test_good_init_data_from_loopback_returns_user(self):
        # sovereign.config.TELEGRAM_BOT_TOKEN is read once at import time from
        # this machine's real ~/.config/estate/estate.env, so an os.environ
        # write here cannot override it (config.py:_env prefers os.environ,
        # but that snapshot already happened). Patch the resolved token
        # instead of the environment.
        with mock.patch.object(auth, "_bot_token", return_value=DUMMY_TOKEN):
            init_data = build_init_data(DUMMY_TOKEN, {"id": int(ALLOWED_ID)})
            user = auth.authorize(init_data, "127.0.0.1")
            self.assertEqual(user["id"], int(ALLOWED_ID))


if __name__ == "__main__":
    unittest.main()
