"""crew#586 CP4: the 24-hour line rides the estate's own Telegram bot, and @conscience answers only the founder.

Shape tests: the daily cron exists and gates the founder-line step; the send is the same
Telegram bot ping.yml uses (no new account); the @conscience handler fires only on the
repository owner's comment, reaches the estate router by lane name (LAW 34: no vendor model
id), and derives the host from ESTATE_ZONE (LAW 46: no zone typed here).
"""
import pathlib
import re

WF = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"
CON = (WF / "conscience.yml").read_text()
ASK = (WF / "conscience-ask.yml").read_text()


def test_daily_line_is_its_own_cron_and_gates_the_step():
    assert 'cron: "23 7 * * *"' in CON
    assert "github.event.schedule == '23 7 * * *'" in CON


def test_line_uses_the_estate_telegram_bot_not_a_new_one():
    assert "SEED_HERMES_TELEGRAM_BOT_TOKEN" in CON and "SEED_HERMES_TELEGRAM_HOME_CHANNEL" in CON
    assert "api.telegram.org" in CON


def test_ask_fires_only_for_the_owner_and_the_mention():
    assert "github.event.comment.user.login == github.repository_owner" in ASK
    assert "startsWith(github.event.comment.body, '@conscience')" in ASK


def test_ask_names_a_router_lane_and_no_vendor_or_zone():
    assert "SEED_HERMES_LITELLM_API_KEY" in ASK
    assert 'awk \'$1=="ESTATE_ZONE:"' in ASK and "llm.{zone}" in ASK
    assert not re.search(r"(claude-|gpt-|gemini-\d|anthropic\.com|openai\.com|mumchimp\.com)", ASK)
