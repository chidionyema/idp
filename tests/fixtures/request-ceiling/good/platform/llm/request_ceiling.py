"""The per-request ceiling. One call may not carry more context than a working turn needs.

WHY THIS EXISTS, measured 2026-09-13. Prefix caching was on and correct ($0.025/M against
$0.150 list). The bill was not price, it was VOLUME:

    key laptop-20260829T143252Z   439 calls   86,525,924 input tokens in 60 minutes   $2.63
    every other key on the estate, summed:                                            568 tokens
    largest single call: 737,169 tokens in / 436 out                       (3,685 : 1)

A session re-sent 737,169 tokens of history on every turn to get ~200 tokens back, 439 times
in an hour. It climbed all session -- 412,894 at the start of the hour, 736,184 by the end.

WHY THE EXISTING GUARDS DID NOT STOP IT, both checked rather than assumed:

  * `platform/llm/spend-breaker-digest.yaml` already grades TOKENS, at 2,000,000 per hour. That
    hour was 86,525,924 -- 43x the threshold -- and it did not sever. It grades the hour's TOTAL,
    so one session sending 737k per call looks exactly like 200 sessions sending 3.7k each. It
    also notifies without refusing, which is its own comment: "It reports and warns; it does not
    sever the router."
  * `~/.pi/agent/models.json` carries a contextWindow per lane, and that is what makes pi compact.
    It is one file on one laptop in one home directory. Fixing it there fixed this machine and
    proved nothing about the estate; a second laptop, a container or a CI runner has its own copy.

So the fix belongs HERE. This is the router every call on the estate passes through, and this
hook can REFUSE -- "raise exception if invalid" -- rather than report after the money is spent.

WHAT IT REFUSES. A single request whose input exceeds MAX_INPUT_TOKENS. The number is a WORKING
window, not a model maximum: every lane here genuinely holds far more (measured from
/v1/model/info; several hold 1,048,576), and that is exactly why nothing stopped. A limit set at
the model's real ceiling can never fire, because the ceiling is where the failure lives.

A request over the limit is not throttled, truncated or silently shrunk. It is refused, loudly,
with the measured size and the ceiling in the message and the fix in the same sentence -- because
a caller that gets a 400 it does not understand will retry, and a retry loop is how one bad call
becomes 439 of them.
"""

import logging
import os
from typing import Any, Literal, Optional, Union

log = logging.getLogger("estate.request-ceiling")

# LiteLLM is present in the router image and absent everywhere else -- the CI runner and a
# laptop cannot import it. The ceiling's LOGIC must be testable from both, so the dependency is
# taken at the point of use and the module stays importable without it. A hook that can only be
# tested inside one image is a hook whose refusal nobody has ever seen fire.
try:
    from litellm.integrations.custom_logger import CustomLogger
except (
    ModuleNotFoundError
):  # pragma: no cover - exercised on any machine without litellm

    class CustomLogger:  # type: ignore[no-redef]
        """Stand-in so `measure` and the hook body stay importable outside the router image."""

        async def async_pre_call_hook(self, *a, **k):  # noqa: D102
            raise NotImplementedError


# 128,000, matching the working window every lane in ~/.pi/agent/models.json now declares. Above
# any real working turn; low enough that the trigger fires while the saving is still real.
MAX_INPUT_TOKENS = int(os.environ.get("ESTATE_MAX_INPUT_TOKENS", "128000"))

# Characters per token, the same 4:1 pi's own estimator uses, so the router and the client agree
# on what a token is. A refusal that fires on a different count than the client's would be
# unfixable from the client side.
CHARS_PER_TOKEN = 4


def _text_len(content: Any) -> int:
    """Length of the text in one message's content, whatever shape the caller sent."""
    if isinstance(content, str):
        return len(content)
    total = 0
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                # text blocks carry `text`; a tool result is under `content`
                total += len(part.get("text") or "")
                total += len(part.get("content") or "")
            elif isinstance(part, str):
                total += len(part)
    return total


def measure(data: dict) -> int:
    """Estimated input tokens for a request body.

    Deliberately an over-estimate rather than an under-estimate: it counts the message text and
    then the serialised tool schemas, which is the part a naive count of `messages` misses and
    the part that grows silently as a session accumulates tools.
    """
    chars = 0
    for message in data.get("messages") or []:
        if isinstance(message, dict):
            chars += _text_len(message.get("content"))
            chars += len(str(message.get("tool_calls") or ""))
    # tool schemas ride on every call and are not in `messages`
    for tool in data.get("tools") or []:
        chars += len(str(tool))
    return chars // CHARS_PER_TOKEN


class EstateRequestCeiling(CustomLogger):
    """Refuses one call that carries more context than a working turn needs."""

    @staticmethod
    def _key_hint(user_api_key_dict: Any) -> str:
        """The LAST 8 characters of the key -- what LiteLLM itself uses to shorten a key.

        Not the first 8: every key here begins `sk-`, so a first-8 prefix is `sk-` plus five
        characters and cannot tell two callers apart, which is the only reason to include it.
        Never the whole key -- this string reaches logs, and a key in a log is a key leaked.
        """
        try:
            raw = getattr(user_api_key_dict, "api_key", "") or ""
            return raw[-8:] if raw else "unknown"
        except Exception:
            return "unknown"

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, Literal["completion", "text_completion", "embeddings"]],
    ) -> Optional[Union[Exception, str, dict]]:
        estimated = measure(data)
        if estimated <= MAX_INPUT_TOKENS:
            return None

        key_hint = self._key_hint(user_api_key_dict)
        model = data.get("model", "unknown")
        log.error(
            "REFUSED request: %s sent ~%s input tokens, ceiling is %s (key %s)",
            model,
            f"{estimated:,}",
            f"{MAX_INPUT_TOKENS:,}",
            key_hint,
        )

        return (
            f"This request carries approximately {estimated:,} input tokens and the estate's "
            f"ceiling is {MAX_INPUT_TOKENS:,} per call (key ...{key_hint}). Refused before it "
            f"was sent, so nothing was billed.\n\n"
            f"That is not a model limit -- this lane holds far more. It is the estate's working "
            f"window: a single call carrying hundreds of thousands of tokens is a conversation "
            f"re-sending its whole history, and on 2026-09-13 that pattern pushed 86,525,924 "
            f"tokens through one hour at an average of 197,098 per call.\n\n"
            f"The fix is compaction, not a retry: this session's context is larger than any turn "
            f"needs. Retrying the same request will be refused identically."
        )


proxy_handler_instance = EstateRequestCeiling()
