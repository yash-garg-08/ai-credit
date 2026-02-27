"""
Ledger service — the financial core.

Rules:
- NEVER update or delete ledger entries (append-only).
- Balance is ALWAYS derived via SUM(amount).
- Use advisory locks or row-level locking to prevent race conditions.
- Idempotency via idempotency_key (unique constraint).
"""
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientCreditsError
from app.ledger.models import LedgerEntry, TransactionType


async def get_group_balance(db: AsyncSession, group_id: uuid.UUID) -> int:
    """Compute group balance from ledger. Returns integer credits."""
    result = await db.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.group_id == group_id
        )
    )
    return int(result.scalar_one())


async def get_group_balance_for_update(db: AsyncSession, group_id: uuid.UUID) -> int:
    """
    Compute group balance while holding an advisory lock on the group.
    Use this inside a transaction that will also insert a deduction.
    This prevents concurrent deductions from causing over-spend.
    """
    # Advisory lock keyed on group_id — holds until end of transaction
    lock_key = int(group_id.int % (2**31))
    await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

    return await get_group_balance(db, group_id)


async def append_entry(
    db: AsyncSession,
    group_id: uuid.UUID,
    amount: int,
    type: TransactionType,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LedgerEntry:
    """
    Append a ledger entry. If idempotency_key is provided and already exists,
    returns the existing entry (no-op).
    """
    if idempotency_key is not None:
        # Check for existing entry with this key
        result = await db.execute(
            select(LedgerEntry).where(LedgerEntry.idempotency_key == idempotency_key)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

    entry = LedgerEntry(
        group_id=group_id,
        amount=amount,
        type=type,
        idempotency_key=idempotency_key,
        metadata_=metadata,
    )
    db.add(entry)
    await db.flush()
    return entry


async def deduct_credits(
    db: AsyncSession,
    group_id: uuid.UUID,
    amount: int,
    idempotency_key: str,
    metadata: dict[str, Any] | None = None,
) -> LedgerEntry:
    """
    Deduct credits from a group's balance.
    - Acquires advisory lock to prevent race conditions
    - Checks balance >= amount
    - Appends negative ledger entry
    - Idempotent via idempotency_key

    Must be called within a transaction (the caller should commit).
    """
    if amount <= 0:
        raise ValueError("Deduction amount must be positive")

    # Check for idempotent replay
    result = await db.execute(
        select(LedgerEntry).where(LedgerEntry.idempotency_key == idempotency_key)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    balance = await get_group_balance_for_update(db, group_id)
    if balance < amount:
        raise InsufficientCreditsError(balance=balance, required=amount)

    return await append_entry(
        db,
        group_id=group_id,
        amount=-amount,
        type=TransactionType.USAGE_DEDUCTION,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )
