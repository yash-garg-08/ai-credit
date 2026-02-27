"""Tests for ledger correctness — the financial core."""
import uuid

import pytest

from app.ledger.models import TransactionType
from app.ledger.service import append_entry, get_group_balance


@pytest.mark.asyncio
async def test_empty_balance(db, sample_group):
    """New group starts with zero balance."""
    group_id, _ = sample_group
    balance = await get_group_balance(db, group_id)
    assert balance == 0


@pytest.mark.asyncio
async def test_credit_purchase_increases_balance(db, sample_group):
    """Purchasing credits increases the balance."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 1000


@pytest.mark.asyncio
async def test_deduction_decreases_balance(db, sample_group):
    """Usage deduction decreases the balance."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, group_id, amount=-300, type=TransactionType.USAGE_DEDUCTION)
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 700


@pytest.mark.asyncio
async def test_multiple_transactions_sum_correctly(db, sample_group):
    """Balance is always SUM(amount)."""
    group_id, _ = sample_group

    await append_entry(db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, group_id, amount=-200, type=TransactionType.USAGE_DEDUCTION)
    await append_entry(db, group_id, amount=-150, type=TransactionType.USAGE_DEDUCTION)
    await append_entry(db, group_id, amount=500, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, group_id, amount=50, type=TransactionType.REFUND)
    await db.commit()

    balance = await get_group_balance(db, group_id)
    assert balance == 1000 - 200 - 150 + 500 + 50  # 1200


@pytest.mark.asyncio
async def test_idempotency_key_prevents_duplicate(db, sample_group):
    """Same idempotency_key should not create a second entry."""
    group_id, _ = sample_group

    entry1 = await append_entry(
        db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE, idempotency_key="purchase-1"
    )
    await db.commit()

    entry2 = await append_entry(
        db, group_id, amount=1000, type=TransactionType.CREDIT_PURCHASE, idempotency_key="purchase-1"
    )
    await db.commit()

    assert entry1.id == entry2.id

    balance = await get_group_balance(db, group_id)
    assert balance == 1000  # Not 2000


@pytest.mark.asyncio
async def test_balance_isolated_per_group(db):
    """Each group has its own independent balance."""
    from app.auth.models import User
    from app.core.security import hash_password
    from app.groups.models import Group

    user = User(email="iso@test.com", hashed_password=hash_password("pw"))
    db.add(user)
    await db.flush()

    g1 = Group(name="Group 1", owner_id=user.id)
    g2 = Group(name="Group 2", owner_id=user.id)
    db.add_all([g1, g2])
    await db.flush()

    await append_entry(db, g1.id, amount=500, type=TransactionType.CREDIT_PURCHASE)
    await append_entry(db, g2.id, amount=300, type=TransactionType.CREDIT_PURCHASE)
    await db.commit()

    assert await get_group_balance(db, g1.id) == 500
    assert await get_group_balance(db, g2.id) == 300
