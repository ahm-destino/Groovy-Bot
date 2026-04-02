from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.services.whatsapp import whatsapp_service
from app.services.interaction_tracking import record_interaction_sent
from app.models import Conversation


def _menu_rows() -> List[Dict[str, str]]:
    return [
        {"id": "action:discover", "title": "Discover events", "description": "Near me, Lagos, this weekend"},
        {"id": "action:my_tickets", "title": "My tickets", "description": "View your tickets"},
        {"id": "action:recommend", "title": "Recommendations", "description": "Suggested events"},
        {"id": "action:create_event", "title": "Create event", "description": "Host a new event"},
        {"id": "action:manage_events", "title": "Manage events", "description": "Stats, broadcast, attendees"},
        {"id": "action:gift_ticket", "title": "Gift tickets", "description": "Send a gift"},
        {"id": "action:help", "title": "Help", "description": "How it works"}
    ]


async def _track_menu(
    phone: str,
    rows: List[Dict[str, str]],
    db: Optional[AsyncSession],
    context: str
):
    if not db:
        return
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)

    log = await record_interaction_sent(
        db=db,
        phone=phone,
        kind="list",
        context=context,
        options=rows
    )
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state["last_interaction_id"] = str(log.id)
    conversation.flow_state["last_interaction_option_ids"] = [r["id"] for r in rows]
    flag_modified(conversation, "flow_state")
    await db.commit()


async def send_main_menu(phone: str, db: Optional[AsyncSession] = None):
    message = "I'm Stefan! Here's your menu. Pick what you'd like to do:"
    rows = _menu_rows()
    await whatsapp_service.send_list(
        phone=phone,
        message=message,
        button_text="Menu",
        sections=[
            {
                "title": "Quick actions",
                "rows": rows
            }
        ]
    )
    await _track_menu(phone, rows, db, "main_menu")


async def send_back_to_menu(phone: str, db: Optional[AsyncSession] = None):
    await whatsapp_service.send_interactive(
        phone=phone,
        message="Back to menu:",
        buttons=[
            {"id": "action:menu", "title": "Menu"}
        ]
    )
    if db:
        await _track_menu(phone, [{"id": "action:menu", "title": "Menu", "description": ""}], db, "back_to_menu")
