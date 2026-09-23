"""Step 2 of spec 2.3: photo in, structured JSON out.

The model is reached through the LiteLLM proxy the estate already runs
(LAW 43: LiteLLM is the mature tool; the alternative rejected is a per-
provider SDK, which would make this file name a provider). The request is
the OpenAI-shaped chat body LiteLLM accepts for every vision-capable
backend, and the alias it names comes from config, so this file holds no
model name (R8, cp25 "Model is configuration").

`VisionCall` is the one seam: a callable taking the model alias and the
messages and returning the raw content string. Tests pass a stub through it
so no paid model is ever called from a test.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from sovereign.intake import config_keys as ck

VisionCall = Callable[[str, list[dict[str, Any]]], str]


class ExtractionError(ValueError):
    """The model did not return the strict JSON the prompt demands."""


@dataclass(frozen=True)
class Extraction:
    markdown: str
    slug: str
    tags: tuple[str, ...]
    title: str
    model: str


def vision_model() -> str:
    """intake.vision_model (SB_VISION_MODEL) when set, else model.vision."""
    alias = str(ck.get("intake.vision_model")).strip()
    if alias:
        return alias
    from sovereign import config

    return str(config.get("model.vision").value)


def system_prompt() -> str:
    return str(ck.get("intake.system_prompt")).format(
        slug_words=ck.get("intake.slug_words"), tag_count=ck.get("intake.tag_count")
    )


def messages_for(image: bytes, caption: str, mime: str | None = None) -> list[dict[str, Any]]:
    mime = mime or str(ck.get("intake.image_mime_default"))
    url = (
        f"{ck.get('intake.image_data_url_prefix')}{mime}"
        f"{ck.get('intake.image_data_url_encoding')}{base64.b64encode(image).decode()}"
    )
    return [
        {"role": "system", "content": system_prompt()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": caption},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        },
    ]


def litellm_call(model: str, messages: list[dict[str, Any]]) -> str:
    """The production VisionCall: one POST to the LiteLLM proxy."""
    from sovereign import config

    if not config.LITELLM_BASE_URL:
        raise ExtractionError("LITELLM_BASE_URL not configured")
    headers = {"Authorization": f"Bearer {config.LITELLM_API_KEY}"} if config.LITELLM_API_KEY else {}
    body = {
        "model": model,
        "messages": messages,
        "temperature": ck.get("intake.temperature"),
        "max_tokens": ck.get("intake.max_tokens"),
        "response_format": {"type": "json_object"},
    }
    url = str(config.LITELLM_BASE_URL) + config.LITELLM_CHAT_COMPLETIONS_PATH
    with httpx.Client(timeout=float(ck.get("intake.timeout_s"))) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or [{}]
    return str((choices[0].get("message") or {}).get("content", ""))


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def sanitize_slug(raw: str) -> str:
    """A filename the repo can hold: lower-case, `_` between words, capped."""
    slug = _SLUG_RE.sub("_", str(raw).lower()).strip("_")
    limit = int(ck.get("intake.slug_max_len"))
    return slug[:limit].strip("_")


def parse(content: str, model: str) -> Extraction:
    """Strict: the reply is one JSON object with the four keys, or it is
    an error. A model that wrapped the object in a code fence is tolerated
    because that is the only common deviation and it loses no data."""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline >= 0 else text
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"model reply is not JSON ({e.msg})") from e
    if not isinstance(obj, dict):
        raise ExtractionError("model reply is JSON but not an object")
    missing = [k for k in ("markdown", "slug", "tags") if k not in obj]
    if missing:
        raise ExtractionError(f"model reply lacks keys {missing}")
    slug = sanitize_slug(str(obj["slug"]))
    if not slug:
        raise ExtractionError("model slug sanitizes to nothing")
    tags_raw = obj["tags"]
    if isinstance(tags_raw, str):
        tags_raw = [t for t in re.split(r"[,\s]+", tags_raw) if t]
    tags = tuple(sanitize_slug(str(t)) for t in tags_raw if sanitize_slug(str(t)))
    return Extraction(
        markdown=str(obj["markdown"]),
        slug=slug,
        tags=tags,
        title=str(obj.get("title") or slug),
        model=model,
    )


def extract(image: bytes, caption: str, *, call: VisionCall | None = None, mime: str | None = None) -> Extraction:
    model = vision_model()
    content = (call or litellm_call)(model, messages_for(image, caption, mime))
    return parse(content, model)
