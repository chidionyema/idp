"""Instant Telegram VIP briefing and 1-tap callback service.

WHY this exists. The founder reads Telegram, not dashboards, and reads it on a
phone or through glasses while walking. So a proposal that scores above the VIP
threshold has to arrive as ONE compact card that can be judged in three seconds,
with the raw evidence folded away and reachable in one tap. A wall of metrics is
not a briefing; it is a transfer of reading work to the founder.

The shape is Telegram Bot API 10 HTML:

  * `<blockquote expandable>` holds the topology, the metric context and the
    verified benchmark receipts, so the card's visible surface stays scannable.
  * `message_effect_id` fires a visual effect on a PLATINUM briefing.
  * `inline_keyboard` carries the decisions: approve, shadow-test, reject, and a
    1-5 star rating. One tap, no typing.
  * `reply_parameters` anchors the card under the founder's pinned control
    message so it lands in one place.

ANTI-SPAM IS PART OF THE FEATURE, NOT A LIMITATION. A channel that pings on
every proposal is a channel the founder mutes, and a muted channel is a dead
channel. So a proposal below the score threshold is never sent, and the hourly
cap coalesces a burst into the silent digest. What the founder sees is the
things that earned attention.

HARNESS-AGNOSTIC. Standard library only: `urllib.request` speaks to the Bot
API, and `transport_fn` is injectable so every test and every alternate
transport (a queue, a different Bot, an XREAL bridge) is possible without
touching this module. No model vendor, no agent SDK, no hook framework.

FAIL-CLOSED ON DELIVERY. A card that could not be delivered is raised, never
counted as sent. A silent failure here reads as "the founder decided nothing",
which is the one outcome this module must never produce.
"""

from __future__ import annotations

import html
import json
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .dream_reflect import (
    DreamReflectEngine,
    EstateTopologySnapshot,
    ScoredDreamProposal,
)

__all__ = [
    "TelegramTransport",
    "TelegramVipConfig",
    "TelegramVipService",
    "VipDispatchResult",
    "VipDeliveryError",
    "render_vip_telegram_payload",
]


class VipDeliveryError(RuntimeError):
    """Raised when a VIP card could not be delivered. Never swallowed."""


@dataclass(frozen=True)
class TelegramVipConfig:
    bot_token: str
    chat_id: str
    founder_surface_url: str = "https://genesis-founder-surface.pages.dev"
    pinned_control_msg_id: int = 3327
    vip_instant_threshold: float = 8.0
    max_instant_vip_per_hour: int = 3
    platinum_effect_id: str = "5104841245755180586"  # Fire visual effect on Platinum briefings


@dataclass(frozen=True)
class VipDispatchResult:
    proposal_id: str
    delivery_mode: str  # "INSTANT_VIP_SENT" | "QUEUED_SILENT_DIGEST"
    telegram_message_id: Optional[int]
    payload: dict[str, Any]


TelegramTransport = Callable[[str, dict[str, Any]], dict[str, Any]]


def _default_telegram_transport(
    bot_token: str, method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        # FM:vip.delivery-failed
        raise VipDeliveryError(
            f"Telegram {method} answered HTTP {exc.code}: {body}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # FM:vip.delivery-failed
        raise VipDeliveryError(f"Telegram {method} could not be delivered: {exc}") from exc


def render_vip_telegram_payload(
    proposal: ScoredDreamProposal,
    topology: EstateTopologySnapshot,
    config: TelegramVipConfig,
) -> dict[str, Any]:
    """Builds a Telegram Bot API 10 HTML VIP card with expandable details and 1-tap actions."""
    badge = {
        "PLATINUM": "💎 VIP PLATINUM",
        "GOLD": "🥇 VIP GOLD",
        "SILVER": "⚪ DIGEST SILVER",
    }.get(proposal.vip_tier, "⚪ DIGEST")

    seal_label = (
        "FOUNDER ES256 SEAL" if proposal.requires_founder_seal else "AUTO-LANE (GREENLANE)"
    )
    budget_left = topology.budget_remaining_uusd / 1_000_000
    budget_cap = topology.budget_cap_uusd / 1_000_000

    e_title = html.escape(proposal.title)
    e_pitch = html.escape(proposal.executive_pitch)
    e_delta = html.escape(proposal.expected_metric_delta)
    e_bottleneck = html.escape(proposal.current_bottleneck)
    e_change = html.escape(proposal.proposed_change)
    e_rollback = html.escape(proposal.rollback_plan)
    e_benchmarks = html.escape(", ".join(proposal.verified_benchmark_ids))
    e_paths = html.escape(", ".join(proposal.touched_paths) or "none")
    e_state = html.escape(proposal.state)
    rating_line = (
        f"\n<b>Founder Review:</b> {'⭐' * proposal.founder_rating} ({proposal.founder_rating}/5)"
        if proposal.founder_rating
        else ""
    )

    text = (
        f"<b>{badge} ({proposal.composite_score:.1f}/10) · {html.escape(proposal.target)}</b>\n"
        f"<b>{e_title}</b>\n"
        f"<code>{html.escape(proposal.proposal_id)}</code> · Agent: "
        f"<code>{html.escape(proposal.agent_id)}</code> · {seal_label}\n\n"
        f"<b>Pitch:</b> {e_pitch}\n"
        f"<b>Delta:</b> <code>{e_delta}</code>\n"
        f"<b>Status:</b> <code>{e_state}</code>{rating_line}\n\n"
        f"<blockquote expandable>"
        f"<b>Live Topology &amp; Metrics</b>\n"
        f"• Lanes: L1={html.escape(topology.lane1_edge_status)} | "
        f"L2={html.escape(topology.lane2_oci_status)} | "
        f"L3={html.escape(topology.lane3_greenlane_status)}\n"
        f"• Discovery: Gortex={html.escape(topology.gortex_status)} | "
        f"Cortex={html.escape(topology.cortex_status)}\n"
        f"• Mac Thin-Client: {topology.mac_free_mib} MiB free | load {topology.mac_load_1m:.1f}\n"
        f"• Budget: ${budget_left:.2f}/${budget_cap:.2f} | "
        f"Tier-0 Cache: {topology.tier0_cache_hit_pct:.0f}% | "
        f"Interrupts(24h): {topology.founder_interrupts_24h} | "
        f"Yield(24h): {topology.operational_yield_24h}\n\n"
        f"<b>Bottleneck:</b> {e_bottleneck}\n"
        f"<b>Proposed Change:</b> {e_change}\n"
        f"<b>Touched Paths:</b> <code>{e_paths}</code>\n"
        f"<b>Verified Benchmarks:</b> <code>{e_benchmarks}</code>\n"
        f"<b>Rollback:</b> {e_rollback}"
        f"</blockquote>"
    )

    pid = proposal.proposal_id
    cockpit_deep_link = f"{config.founder_surface_url.rstrip('/')}/dream/{pid}"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve → Lane", "callback_data": f"vip:{pid}:approve"},
                {"text": "🧪 Shadow-Test", "callback_data": f"vip:{pid}:shadow"},
                {"text": "❌ Reject", "callback_data": f"vip:{pid}:reject"},
            ],
            [
                {"text": "⭐5 Elite", "callback_data": f"vip:{pid}:rate:5"},
                {"text": "⭐3 Useful", "callback_data": f"vip:{pid}:rate:3"},
                {"text": "⭐1 Noise", "callback_data": f"vip:{pid}:rate:1"},
                {"text": "📊 Cockpit", "url": cockpit_deep_link},
            ],
        ]
    }

    payload: dict[str, Any] = {
        "chat_id": config.chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup,
        "reply_parameters": {"message_id": config.pinned_control_msg_id},
    }
    if proposal.vip_tier == "PLATINUM" and config.platinum_effect_id:
        payload["message_effect_id"] = config.platinum_effect_id
    return payload


class TelegramVipService:
    """Instant Telegram VIP delivery with anti-spam rate caps and 1-tap callback processing."""

    def __init__(self, config: TelegramVipConfig, db_path: str = ":memory:") -> None:
        self.config = config
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vip_dispatch_log (
                proposal_id TEXT PRIMARY KEY,
                delivery_mode TEXT NOT NULL,
                telegram_message_id INTEGER,
                payload_json TEXT NOT NULL,
                dispatched_at_epoch INTEGER NOT NULL
            );
            """
        )

    def _instant_sent_last_hour(self, now_epoch: int) -> int:
        cutoff = now_epoch - 3600
        return int(
            self._conn.execute(
                """
                SELECT COUNT(*) FROM vip_dispatch_log
                WHERE delivery_mode = 'INSTANT_VIP_SENT' AND dispatched_at_epoch >= ?
                """,
                (cutoff,),
            ).fetchone()[0]
        )

    def dispatch(
        self,
        proposal: ScoredDreamProposal,
        topology: EstateTopologySnapshot,
        transport_fn: Optional[TelegramTransport] = None,
        now_epoch: Optional[int] = None,
    ) -> VipDispatchResult:
        """Send the card if it earned it, else queue it silently. Never both, never neither."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        payload = render_vip_telegram_payload(proposal, topology, self.config)

        qualifies_instant = proposal.composite_score >= self.config.vip_instant_threshold
        under_rate_cap = self._instant_sent_last_hour(ts) < self.config.max_instant_vip_per_hour

        if qualifies_instant and under_rate_cap:
            sender = transport_fn or (
                lambda method, body: _default_telegram_transport(
                    self.config.bot_token, method, body
                )
            )
            # A transport that raises propagates: an undelivered card is NOT logged as
            # sent, and the digest never picks it up either. The founder must be able to
            # trust that a silence means "nothing was worth sending".
            resp = sender("sendMessage", payload)
            msg_id = int(resp.get("result", {}).get("message_id", 0)) or None
            mode = "INSTANT_VIP_SENT"
        else:
            msg_id = None
            mode = "QUEUED_SILENT_DIGEST"

        self._conn.execute(
            """
            INSERT OR REPLACE INTO vip_dispatch_log (
                proposal_id, delivery_mode, telegram_message_id, payload_json, dispatched_at_epoch
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (proposal.proposal_id, mode, msg_id, json.dumps(payload, sort_keys=True), ts),
        )
        return VipDispatchResult(
            proposal_id=proposal.proposal_id,
            delivery_mode=mode,
            telegram_message_id=msg_id,
            payload=payload,
        )

    def pending_silent_digest(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT proposal_id, payload_json, dispatched_at_epoch
            FROM vip_dispatch_log
            WHERE delivery_mode = 'QUEUED_SILENT_DIGEST'
            ORDER BY dispatched_at_epoch ASC
            """
        ).fetchall()
        return [
            {
                "proposal_id": r[0],
                "payload": json.loads(r[1]),
                "queued_at_epoch": r[2],
            }
            for r in rows
        ]

    def handle_callback(
        self,
        callback_query_id: str,
        callback_data: str,
        message_id: int,
        dream_engine: DreamReflectEngine,
        topology: EstateTopologySnapshot,
        review_note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Processes a 1-tap Founder button press and returns live in-place Telegram update payloads."""
        parts = callback_data.split(":")
        if len(parts) < 3 or parts[0] != "vip":
            # FM:vip.callback-data-invalid
            raise ValueError(f"Invalid VIP callback_data: {callback_data}")

        proposal_id = parts[1]
        action = parts[2]

        if action == "approve":
            updated = dream_engine.record_founder_decision(proposal_id, "APPROVED_FOR_LANE")
            toast = f"Approved {proposal_id} -> queued for Greenlane"
        elif action == "shadow":
            updated = dream_engine.record_founder_decision(proposal_id, "SHADOW_TEST")
            toast = f"Shadow-test started for {proposal_id}"
        elif action == "reject":
            updated = dream_engine.record_founder_decision(proposal_id, "REJECTED")
            toast = f"Rejected {proposal_id}"
        elif action == "rate" and len(parts) == 4:
            rating = int(parts[3])
            updated = dream_engine.record_founder_review(
                proposal_id, rating, review_note=review_note
            )
            toast = f"Recorded {rating}/5 Founder rating on {proposal_id}"
        else:
            # FM:vip.callback-action-unsupported
            raise ValueError(f"Unsupported VIP callback action: {callback_data}")

        refreshed = render_vip_telegram_payload(updated, topology, self.config)
        return {
            "updated_proposal": updated,
            "answerCallbackQuery": {
                "callback_query_id": callback_query_id,
                "text": toast,
                "show_alert": False,
            },
            "editMessageText": {
                "chat_id": self.config.chat_id,
                "message_id": message_id,
                "text": refreshed["text"],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": refreshed["reply_markup"],
            },
        }
