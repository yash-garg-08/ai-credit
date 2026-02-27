"""Multi-tenancy: orgs, workspaces, agent_groups, agents, api_keys, credentials, policies, budgets, audit

Revision ID: 002
Revises: 001
Create Date: 2026-02-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("billing_group_id", sa.UUID(), nullable=False),
        sa.Column("credits_per_usd", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["billing_group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_orgs_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_orgs_owner_id", "organizations", ["owner_id"])

    # --- workspaces ---
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_org_id", "workspaces", ["org_id"])

    # --- agent_groups ---
    op.create_table(
        "agent_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_groups_workspace_id", "agent_groups", ["workspace_id"])

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_group_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DISABLED", "BUDGET_EXHAUSTED", name="agentstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_group_id"], ["agent_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_agent_group_id", "agents", ["agent_group_id"])

    # --- api_keys ---
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_suffix", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_agent_id", "api_keys", ["agent_id"])

    # --- provider_credentials ---
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column(
            "mode",
            sa.Enum("MANAGED", "BYOK", name="credentialmode"),
            nullable=False,
        ),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cred_org_provider", "provider_credentials", ["org_id", "provider"])

    # --- policies ---
    op.create_table(
        "policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("agent_group_id", sa.UUID(), nullable=True),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("allowed_models", sa.JSON(), nullable=True),
        sa.Column("max_input_tokens", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column("rpm_limit", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_group_id"], ["agent_groups.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policies_org_id", "policies", ["org_id"])
    op.create_index("ix_policies_workspace_id", "policies", ["workspace_id"])
    op.create_index("ix_policies_agent_group_id", "policies", ["agent_group_id"])
    op.create_index("ix_policies_agent_id", "policies", ["agent_id"])

    # --- budgets ---
    op.create_table(
        "budgets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("agent_group_id", sa.UUID(), nullable=True),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column(
            "period",
            sa.Enum("DAILY", "MONTHLY", "TOTAL", name="budgetperiod"),
            nullable=False,
        ),
        sa.Column("limit_credits", sa.BigInteger(), nullable=False),
        sa.Column("auto_disable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_group_id"], ["agent_groups.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_org_id", "budgets", ["org_id"])
    op.create_index("ix_budgets_workspace_id", "budgets", ["workspace_id"])
    op.create_index("ix_budgets_agent_group_id", "budgets", ["agent_group_id"])
    op.create_index("ix_budgets_agent_id", "budgets", ["agent_id"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_agent_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_org_id", "audit_logs", ["org_id"])
    op.create_index("ix_audit_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_event_type", "audit_logs", ["event_type"])

    # --- update usage_events: add agent_id, latency_ms, status, error_message ---
    op.add_column("usage_events", sa.Column("agent_id", sa.UUID(), nullable=True))
    op.add_column("usage_events", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column(
        "usage_events",
        sa.Column(
            "status",
            sa.Enum(
                "SUCCESS", "ERROR", "POLICY_BLOCKED", "BUDGET_EXCEEDED",
                name="usagestatus"
            ),
            nullable=False,
            server_default="SUCCESS",
        ),
    )
    op.add_column(
        "usage_events",
        sa.Column("error_message", sa.String(1024), nullable=True),
    )
    op.create_foreign_key(
        "fk_usage_agent_id", "usage_events", "agents", ["agent_id"], ["id"]
    )
    op.create_index("ix_usage_agent_id", "usage_events", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_agent_id", "usage_events")
    op.drop_constraint("fk_usage_agent_id", "usage_events", type_="foreignkey")
    op.drop_column("usage_events", "error_message")
    op.drop_column("usage_events", "status")
    op.drop_column("usage_events", "latency_ms")
    op.drop_column("usage_events", "agent_id")

    op.drop_table("audit_logs")
    op.drop_table("budgets")
    op.drop_table("policies")
    op.drop_table("provider_credentials")
    op.drop_table("api_keys")
    op.drop_table("agents")
    op.drop_table("agent_groups")
    op.drop_table("workspaces")
    op.drop_table("organizations")

    op.execute("DROP TYPE IF EXISTS usagestatus")
    op.execute("DROP TYPE IF EXISTS budgetperiod")
    op.execute("DROP TYPE IF EXISTS credentialmode")
    op.execute("DROP TYPE IF EXISTS agentstatus")
