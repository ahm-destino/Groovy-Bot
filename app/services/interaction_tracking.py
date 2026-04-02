from typing import Any, List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import InteractionLog


async def record_interaction_sent(
    db: AsyncSession,
    phone: str,
    kind: str,
    context: str,
    options: List[Dict[str, Any]]
) -> InteractionLog:
    log = InteractionLog(
        phone=phone,
        kind=kind,
        context=context,
        options=options
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def record_interaction_clicked(
    db: AsyncSession,
    interaction_id: str,
    selected_id: str
) -> Optional[InteractionLog]:
    result = await db.execute(
        select(InteractionLog).where(InteractionLog.id == interaction_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        return None
    log.selected_id = selected_id
    log.selected_at = datetime.utcnow()
    await db.commit()
    await db.refresh(log)
    return log
