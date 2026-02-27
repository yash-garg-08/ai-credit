"""
Tests for workflow idempotency and balance enforcement.

These test the activity logic directly (no Temporal server needed).
Temporal's workflow-level idempotency (workflow ID dedup) is guaranteed
by the Temporal server itself.
"""
import uuid

import pytest

from app.ledger.models import TransactionType
from app.ledger.service import append_entry, get_group_balance


@pytest.mark.asyncio
async def test_idempotent_deduction(db, sample_group):
    """Same idempotency key must not deduct twice."""
    group_id, _ = sample_group

    # Fund the group
    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await db.commit()

    key = f"usage:{uuid.uuid4()}"

    # First deduction
    await append_entry(
        db, group_id, amount=-100, type=TransactionType.USAGE_DEDUCTION, idempotency_key=key
    )
    await db.commit()

    # Duplicate deduction (same key)
    await append_entry(
        db, group_id, amount=-100, type=TransactionType.USAGE_DEDUCTION, idempotency_key=key
    )
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 900  # Only one deduction applied


@pytest.mark.asyncio
async def test_separate_keys_deduct_independently(db, sample_group):
    """Different idempotency keys create separate deductions."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await db.commit()

    await append_entry(
        db, group_id, amount=-100, type=TransactionType.USAGE_DEDUCTION,
        idempotency_key=f"usage:{uuid.uuid4()}"
    )
    await append_entry(
        db, group_id, amount=-200, type=TransactionType.USAGE_DEDUCTION,
        idempotency_key=f"usage:{uuid.uuid4()}"
    )
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 700


@pytest.mark.asyncio
async def test_refund_restores_balance(db, sample_group):
    """Refund entries correctly increase balance."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, group_id, amount=-500, type=TransactionType.USAGE_DEDUCTION)
    await append_entry(db, group_id, amount=200, type=TransactionType.REFUND)
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 700


@pytest.mark.asyncio
async def test_adjustment_entry(db, sample_group):
    """Admin adjustments work correctly."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, group_id, amount=-50, type=TransactionType.ADJUSTMENT,
                       metadata={"reason": "billing correction"})
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 950
