"""Enforce single target level for policies and budgets

Revision ID: 003
Revises: 002
Create Date: 2026-02-27
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_policies_single_target",
        "policies",
        "(CASE WHEN org_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN workspace_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN agent_group_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN agent_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
    )
    op.create_check_constraint(
        "ck_budgets_single_target",
        "budgets",
        "(CASE WHEN org_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN workspace_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN agent_group_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN agent_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_budgets_single_target", "budgets", type_="check")
    op.drop_constraint("ck_policies_single_target", "policies", type_="check")
