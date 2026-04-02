"""
Report generation service for exporting data
"""
import csv
import io
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.models import Event, Booking, Ticket, User


async def generate_bookings_report(
    event_id: str,
    db: AsyncSession
) -> str:
    """
    Generate CSV report for event bookings
    """
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one()

    result = await db.execute(
        select(Booking).where(
            Booking.event_id == event_id
        ).order_by(Booking.booked_at.desc())
    )
    bookings = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Booking ID',
        'Customer Name',
        'Phone',
        'Email',
        'Quantity',
        'Total Amount',
        'Status',
        'Payment Method',
        'Booked At',
        'Confirmed At',
        'Source'
    ])

    for booking in bookings:
        result = await db.execute(
            select(User).where(User.id == booking.user_id)
        )
        user = result.scalar_one_or_none()

        writer.writerow([
            f"GRV-{booking.id.hex[:8].upper()}",
            user.name if user and user.name else 'Guest',
            booking.phone,
            user.email if user else '',
            booking.quantity,
            f"NGN {booking.total_amount:,.2f}",
            booking.status,
            booking.payment_method or 'N/A',
            booking.booked_at.strftime('%Y-%m-%d %H:%M:%S'),
            booking.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if booking.confirmed_at else 'N/A',
            booking.booking_source or 'webapp'
        ])

    return output.getvalue()


async def generate_tickets_report(
    event_id: str,
    db: AsyncSession
) -> str:
    """
    Generate CSV report for event tickets
    """
    result = await db.execute(
        select(Ticket).where(
            Ticket.event_id == event_id
        ).order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Ticket Code',
        'Customer Name',
        'Phone',
        'Status',
        'Entry Code',
        'Checked In',
        'Check-in Time',
        'Created At'
    ])

    for ticket in tickets:
        result = await db.execute(
            select(User).where(User.id == ticket.user_id)
        )
        user = result.scalar_one_or_none()

        result = await db.execute(
            select(Booking).where(Booking.id == ticket.booking_id)
        )
        booking = result.scalar_one_or_none()

        writer.writerow([
            ticket.ticket_code,
            user.name if user and user.name else 'Guest',
            booking.phone if booking else 'N/A',
            ticket.status,
            ticket.entry_code or 'N/A',
            'Yes' if ticket.checked_in_at else 'No',
            ticket.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.checked_in_at else 'N/A',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return output.getvalue()


async def generate_revenue_report(
    organizer_id: str,
    db: AsyncSession,
    start_date: datetime = None,
    end_date: datetime = None
) -> str:
    """
    Generate revenue report for organizer
    """
    query = select(Event).where(Event.host_id == organizer_id)

    if start_date:
        query = query.where(Event.created_at >= start_date)
    if end_date:
        query = query.where(Event.created_at <= end_date)

    result = await db.execute(query.order_by(Event.event_date.desc()))
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Event Title',
        'Event Date',
        'Category',
        'Ticket Price',
        'Capacity',
        'Tickets Sold',
        'Total Bookings',
        'Confirmed Bookings',
        'Total Revenue',
        'Status'
    ])

    total_revenue = 0
    total_tickets = 0

    for event in events:
        result = await db.execute(
            select(Booking).where(
                and_(
                    Booking.event_id == event.id,
                    Booking.status == 'confirmed'
                )
            )
        )
        confirmed_bookings = result.scalars().all()

        result = await db.execute(
            select(Booking).where(Booking.event_id == event.id)
        )
        all_bookings = result.scalars().all()

        event_revenue = sum(b.total_amount for b in confirmed_bookings)
        event_tickets = sum(b.quantity for b in confirmed_bookings)

        total_revenue += event_revenue
        total_tickets += event_tickets

        writer.writerow([
            event.title,
            event.event_date.strftime('%Y-%m-%d %H:%M'),
            event.category or 'N/A',
            f"NGN {event.ticket_price:,.2f}",
            event.capacity,
            event_tickets,
            len(all_bookings),
            len(confirmed_bookings),
            f"NGN {event_revenue:,.2f}",
            event.status
        ])

    writer.writerow([])
    writer.writerow([
        'TOTAL',
        '',
        '',
        '',
        '',
        total_tickets,
        '',
        '',
        f"NGN {total_revenue:,.2f}",
        ''
    ])

    return output.getvalue()
