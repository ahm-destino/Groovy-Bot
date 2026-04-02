"""
Promo code service for discount management
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from decimal import Decimal

from app.models.promo_code import PromoCode
from app.models import Event


async def create_promo_code(
    code: str,
    discount_type: str,
    discount_value: float,
    creator_id: str,
    db: AsyncSession,
    event_id: Optional[str] = None,
    description: Optional[str] = None,
    max_uses: Optional[int] = None,
    valid_until: Optional[datetime] = None,
    min_tickets: int = 1,
    max_discount_amount: Optional[float] = None
) -> PromoCode:
    """
    Create a new promo code
    """
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == code.upper())
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise ValueError("Promo code already exists")

    promo = PromoCode(
        code=code.upper(),
        event_id=event_id,
        description=description,
        discount_type=discount_type,
        discount_value=Decimal(str(discount_value)),
        max_uses=max_uses,
        valid_until=valid_until,
        min_tickets=min_tickets,
        max_discount_amount=Decimal(str(max_discount_amount)) if max_discount_amount else None,
        created_by=creator_id
    )

    db.add(promo)
    await db.commit()
    await db.refresh(promo)

    return promo


async def validate_promo_code(
    code: str,
    event_id: str,
    quantity: int,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Validate a promo code for an event
    """
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == code.upper())
    )
    promo = result.scalar_one_or_none()

    if not promo:
        return {
            'valid': False,
            'promo': None,
            'message': 'Invalid promo code'
        }

    if promo.event_id and str(promo.event_id) != event_id:
        return {
            'valid': False,
            'promo': None,
            'message': 'Promo code not valid for this event'
        }

    is_valid, error_message = promo.is_valid(quantity)

    if not is_valid:
        return {
            'valid': False,
            'promo': promo,
            'message': error_message
        }

    return {
        'valid': True,
        'promo': promo,
        'message': 'Promo code applied successfully'
    }


async def apply_promo_code(
    promo_id: str,
    subtotal: Decimal,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Apply promo code and calculate discount
    """
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_id)
    )
    promo = result.scalar_one()

    discount_amount = promo.calculate_discount(subtotal)
    final_amount = subtotal - discount_amount

    promo.current_uses += 1

    if promo.max_uses and promo.current_uses >= promo.max_uses:
        promo.status = 'expired'

    await db.commit()

    return {
        'discount_amount': discount_amount,
        'final_amount': final_amount,
        'promo': promo
    }


async def get_event_promo_codes(
    event_id: str,
    db: AsyncSession,
    active_only: bool = True
) -> list[PromoCode]:
    """Get all promo codes for an event"""
    query = select(PromoCode).where(PromoCode.event_id == event_id)

    if active_only:
        query = query.where(PromoCode.status == 'active')

    result = await db.execute(query.order_by(PromoCode.created_at.desc()))
    return result.scalars().all()


async def format_promo_info(promo: PromoCode) -> str:
    """Format promo code info for display"""
    message = f"Promo: {promo.code}\n"

    if promo.description:
        message += f"{promo.description}\n"

    if promo.discount_type == 'percentage':
        message += f"{promo.discount_value}% off"
        if promo.max_discount_amount:
            message += f" (max NGN {promo.max_discount_amount:,.0f})"
    else:
        message += f"NGN {promo.discount_value:,.0f} off"

    message += "\n"

    if promo.min_tickets > 1:
        message += f"Min {promo.min_tickets} tickets\n"

    if promo.max_uses:
        remaining = promo.max_uses - promo.current_uses
        message += f"{remaining}/{promo.max_uses} uses left\n"

    if promo.valid_until:
        message += f"Valid until {promo.valid_until.strftime('%b %d, %Y')}\n"

    return message
