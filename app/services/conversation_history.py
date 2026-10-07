"""
Conversation memory for the WhatsApp bot.

The LLM classifier works far better with the recent back-and-forth in context.
Rather than add a new column (and risk a model/DB mismatch on deploy), memory is
reconstructed from the existing ``message_logs`` table:

- inbound rows  -> ``user`` turns
- outbound rows -> ``assistant`` turns (only the conversational replies we log)

Both reading and writing are best-effort: any failure here is logged and
swallowed so it can never break message processing.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MessageLog

logger = logging.getLogger(__name__)

# Inbound payloads that are interactive IDs / control tokens, not natural
# language — excluded from history so the model sees real conversation only.
_STRUCTURED_PREFIXES = (
    "action:", "event:", "pay_", "refund:", "refund_confirm:", "refund_cancel:",
    "org_event:", "org_action:", "gift_history:", "gift_qty:", "gift_skip",
    "share_ticket:", "rec:", "help:", "book_",
)

_PER_MESSAGE_CHAR_CAP = 300


def _is_meaningful(content: Optional[str]) -> bool:
    if not content:
        return False
    text = content.strip()
    if not text:
        return False
    if text.lower().startswith(_STRUCTURED_PREFIXES):
        return False
    # Bare numbers are list selections, not conversational content.
    if text.isdigit():
        return False
    return True


def _clip(text: str) -> str:
    text = text.strip()
    if len(text) > _PER_MESSAGE_CHAR_CAP:
        return text[:_PER_MESSAGE_CHAR_CAP].rstrip() + "..."
    return text


async def get_recent_history(
    phone: str,
    db: AsyncSession,
    limit: int = 10,
    max_chars: int = 4000,
    exclude_message_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Return up to ``limit`` recent turns (oldest first) as
    ``{"role": "user"|"assistant", "content": str}``.

    ``exclude_message_id`` drops the current inbound message (already logged by
    the webhook before classification runs). Total content is capped at
    ``max_chars``, keeping the most recent turns.
    """
    try:
        # Pull a few extra rows so filtering still leaves ~limit turns.
        fetch = max(limit * 3, limit + 5)
        result = await db.execute(
            select(MessageLog)
            .where(MessageLog.phone == phone)
            .order_by(MessageLog.created_at.desc())
            .limit(fetch)
        )
        rows = result.scalars().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_recent_history failed for %s: %s", phone, exc)
        return []

    turns: List[Dict[str, str]] = []
    budget = max_chars
    for row in rows:  # newest -> oldest
        if exclude_message_id and row.whatsapp_message_id == exclude_message_id:
            continue
        if row.direction not in ("inbound", "outbound"):
            continue
        if not _is_meaningful(row.content):
            continue
        content = _clip(row.content)
        if len(content) > budget:
            break
        budget -= len(content)
        role = "user" if row.direction == "inbound" else "assistant"
        turns.append({"role": role, "content": content})
        if len(turns) >= limit:
            break

    turns.reverse()  # oldest -> newest for the LLM
    return turns


async def log_outbound(
    phone: str,
    text: str,
    db: AsyncSession,
    intent: Optional[str] = None,
) -> None:
    """
    Persist an assistant conversational reply as an outbound ``message_logs`` row
    so it becomes part of future history. Best-effort: never raises.
    """
    if not text or not text.strip():
        return
    try:
        db.add(
            MessageLog(
                phone=phone,
                direction="outbound",
                message_type="text",
                content=text.strip()[:4000],
                intent_detected=intent,
            )
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("log_outbound failed for %s: %s", phone, exc)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
