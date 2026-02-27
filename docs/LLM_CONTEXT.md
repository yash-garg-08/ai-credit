# LLM Context — AI Agent Governance & Control Platform

This file is optimized for fast, complete ingestion by an LLM. It encodes the full project in a dense, structured format with no prose padding.

---

## IDENTITY

- **What:** Multi-tenant SaaS backend. Orgs deploy AI agents. Every agent call is proxied through a governance gateway that enforces policies, checks budgets, and deducts credits from an immutable ledger.
- **Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 async · asyncpg · Pydantic v2 · Temporal · httpx · PostgreSQL 16 · Redis 7 · React 18 + TypeScript + Vite + Tailwind · nginx · Docker Compose
- **Root:** `~/Desktop/ai-credit-platform`
- **Version:** 2.0.0

---

## ENTITY HIERARCHY

```
Organization (top-level billing tenant)
  billing_group_id ──→ groups.id  (ledger account)
  ├── ProviderCredential[]  (BYOK, Fernet-encrypted)
  ├── Policy[]              (can target any level)
  ├── Budget[]              (can target any level)
  └── Workspace[]
        └── AgentGroup[]
              └── Agent[]
                    └── ApiKey[]  (cpk_*** keys, SHA-256 hash only)
```

Users (human) authenticate via JWT. Agents authenticate via `cpk_` API keys.

---

## CRITICAL INVARIANTS

1. **No stored balance.** `balance = SELECT SUM(amount) FROM ledger WHERE group_id = $1`. Never a cached column.
2. **No double deduction.** Temporal workflow ID = `request_id` UUID. Temporal deduplicates. DB: unique `idempotency_key` column.
3. **No race condition.** `pg_advisory_xact_lock(int(group_id.int % 2**31))` held for duration of balance-check + deduction insert inside one transaction.
4. **Credits are integers.** `BIGINT`. Cost rounded UP (`math.ceil`) to avoid under-charging.
5. **API keys never stored.** Only `SHA-256(key)` persisted. `key_suffix` (last 8 chars) for display only.
6. **BYOK keys encrypted.** Fernet AES-256. `CREDENTIAL_ENCRYPTION_KEY` env var. Auto-generated in dev (keys lost on restart).
7. **Ledger append-only.** No UPDATE or DELETE on `ledger` rows ever.
8. **Audit append-only.** No UPDATE or DELETE on `audit_logs` rows ever.

---

## FILE MAP

```
app/
  config.py              Settings(BaseSettings): database_url, redis_url, temporal_host,
                         temporal_task_queue, secret_key, algorithm, openai_api_key,
                         openai_base_url, credential_encryption_key, credits_per_usd,
                         db_pool_size, db_max_overflow

  main.py                FastAPI app. Includes all 15 routers. Lifespan disposes engine
                         and closes provider HTTP clients.

  db/
    base.py              Base(DeclarativeBase), UUIDMixin(Uuid pk, uuid4 default),
                         TimestampMixin(DateTime timezone=True, server_default=now())
    session.py           create_async_engine + async_session_factory

  core/
    security.py          bcrypt (NOT passlib — compat issue Python 3.13).
                         hash_password(), verify_password(), create_access_token(),
                         decode_access_token()
    dependencies.py      get_db() → AsyncSession, get_current_user() → User,
                         DbSession = Annotated[...], CurrentUser = Annotated[...]
    exceptions.py        AppError(message, status_code=400)  ← NOTE: message is FIRST arg
                         InsufficientCreditsError(balance, required) → 402
                         NotFoundError(entity, id) → 404
                         ForbiddenError(message) → 403

  auth/
    models.py            User: id(Uuid), email(String 320, unique), hashed_password(String 128)
    service.py           register_user(), authenticate_user()
    router.py            POST /auth/register, POST /auth/login

  groups/  [LEGACY]
    models.py            Group: id, name, owner_id(FK users)
                         Membership: id, user_id(FK), group_id(FK), role(MemberRole enum)
                         MemberRole: ADMIN | MEMBER
    service.py           create_group(), get_user_membership(), invite_user()
    router.py            POST /groups, GET /groups/me, POST /groups/{id}/invite,
                         GET /groups/{id}/balance

  ledger/
    models.py            LedgerEntry: id, group_id(FK groups), amount(BigInteger signed),
                         type(TransactionType enum), idempotency_key(String 255 unique nullable),
                         metadata_(JSON)
                         TransactionType: CREDIT_PURCHASE | USAGE_DEDUCTION | ADJUSTMENT | REFUND
    service.py           get_group_balance(db, group_id) → int
                         get_group_balance_for_update(db, group_id) → int  [acquires advisory lock]
                         append_entry(db, group_id, amount, type, idempotency_key, metadata)
                         deduct_credits(db, group_id, amount, idempotency_key, metadata)
                           ↳ checks idempotent replay first
                           ↳ calls get_group_balance_for_update (advisory lock)
                           ↳ raises InsufficientCreditsError if balance < amount
                           ↳ inserts negative entry
    router.py            POST /credits/purchase

  usage/
    models.py            UsageEvent: id, user_id(FK), group_id(FK groups), agent_id(FK agents nullable),
                         provider(String 64), model(String 128), input_tokens(BigInt),
                         output_tokens(BigInt), total_tokens(BigInt), cost_usd(Numeric 18,8),
                         credits_charged(BigInt), latency_ms(Integer nullable),
                         status(UsageStatus enum default SUCCESS), error_message(String 1024 nullable)
                         UsageStatus: SUCCESS | ERROR | POLICY_BLOCKED | BUDGET_EXCEEDED
    service.py           record_usage_event(...) — supports all new fields, all nullable have defaults
                         get_usage_history(db, group_id, limit, offset)
                         get_burn_rate(db, group_id) → (int, int)  [24h, 7d]
                         get_top_users(db, group_id, limit) → [(user_id, total_credits)]
    router.py            POST /usage/request [calls provider then Temporal workflow]
                         GET /usage/history/{group_id}
                         GET /usage/burn-rate/{group_id}
                         GET /usage/top-users/{group_id}

  pricing/
    models.py            PricingRule: id, provider(String 64), model(String 128),
                         input_cost_per_1k(Numeric 18,8), output_cost_per_1k(Numeric 18,8)
                         Unique index: (provider, model)
    service.py           get_pricing_rule(db, provider, model) → PricingRule
                         calculate_cost(rule, input_tokens, output_tokens) → Decimal
                         cost_to_credits(cost_usd) → int  [math.ceil, rounds up]
                         compute_usage_cost(db, provider, model, input, output) → CostCalculation
    router.py            GET /pricing

  providers/
    base.py              ProviderResponse(content, input_tokens, output_tokens, total_tokens, raw_metadata)
                         BaseProvider(ABC): provider_name, generate_completion(model, messages, **kwargs)
    openai.py            OpenAIProvider: uses settings.openai_api_key + settings.openai_base_url
    anthropic.py         AnthropicProvider(api_key): POST /messages endpoint.
                         Splits system message from messages list. Converts to Anthropic format.
    mock.py              MockProvider: deterministic, no external calls. token_count = input_chars//4
    registry.py          get_provider(name) → singleton BaseProvider  [platform keys]
                         make_provider(name, api_key) → ephemeral BaseProvider  [BYOK]
                         close_all() → cleanup

  workflows/
    activities.py        @activity.defn: fetch_pricing, calculate_cost, check_balance_and_limits,
                         record_usage_and_deduct
                         Inputs/outputs are dataclasses. Decimal serialized as str.
    process_usage.py     @workflow.defn ProcessUsageWorkflow:
                         Step 1: fetch_pricing (3 retries, 10s timeout)
                         Step 2: calculate_cost (pure computation, 5s timeout)
                         Step 3: check_balance_and_limits (3 retries, 10s timeout)
                         Step 4: record_usage_and_deduct (3 retries, 15s timeout)
                         Workflow ID = "usage-{request_id}" → Temporal deduplication
    worker.py            Connects to settings.temporal_host, task_queue="credit-platform",
                         registers all 4 activities + ProcessUsageWorkflow

  orgs/
    models.py            Organization: id, name, slug(unique), owner_id(FK users),
                         billing_group_id(FK groups), credits_per_usd(Integer default 100),
                         is_active(Boolean), description(Text nullable)
    service.py           create_organization(db, owner_id, name, description)
                           ↳ auto-creates a Group for billing + adds owner as ADMIN membership
                           ↳ slugifies name, deduplicates
                         get_org(db, org_id), list_orgs_for_user(db, user_id)
    router.py            POST /orgs, GET /orgs, GET /orgs/{org_id}/balance

  workspaces/
    models.py            Workspace: id, org_id(FK orgs), name, slug, description, is_active
    service.py           create_workspace, list_workspaces, get_workspace
    router.py            POST /orgs/{org_id}/workspaces, GET /orgs/{org_id}/workspaces

  agent_groups/
    models.py            AgentGroup: id, workspace_id(FK workspaces), name, description, is_active
    service.py           create_agent_group, list_agent_groups, get_agent_group
    router.py            POST /workspaces/{workspace_id}/agent-groups
                         GET /workspaces/{workspace_id}/agent-groups

  agents/
    models.py            Agent: id, agent_group_id(FK agent_groups), name, description,
                         status(AgentStatus enum default ACTIVE)
                         AgentStatus: ACTIVE | DISABLED | BUDGET_EXHAUSTED
                         ApiKey: id, agent_id(FK agents), name, key_hash(String 64 unique),
                         key_suffix(String 8), is_active(Boolean), revoked_reason(Text nullable)
    service.py           _generate_platform_key() → "cpk_" + base64url(32 random bytes)
                         _hash_key(key) → SHA-256 hex
                         create_api_key(db, agent_id, name) → (ApiKey, plaintext_key)
                         resolve_api_key(db, plaintext_key) → ApiKey | None  [hash lookup]
                         revoke_api_key(db, api_key_id, reason)
                         create_agent, list_agents_for_group, get_agent, disable_agent
    router.py            POST /agent-groups/{id}/agents, GET /agent-groups/{id}/agents
                         POST /agents/{id}/keys, DELETE /agents/{id}/keys/{key_id}

  credentials/
    models.py            ProviderCredential: id, org_id(FK orgs), provider(String 64),
                         mode(CredentialMode enum: MANAGED|BYOK), encrypted_api_key(Text),
                         is_active, label
    service.py           encrypt_key(plaintext) → ciphertext  [Fernet]
                         decrypt_key(ciphertext) → plaintext
                         add_credential(db, org_id, provider, plaintext_api_key, label, mode)
                         get_active_credential(db, org_id, provider) → str | None  [decrypted]
    router.py            POST /orgs/{org_id}/credentials

  policies/
    models.py            Policy: id, org_id|workspace_id|agent_group_id|agent_id (exactly one set),
                         name, allowed_models(JSON nullable), max_input_tokens(Integer nullable),
                         max_output_tokens(Integer nullable), rpm_limit(Integer nullable), is_active
    service.py           EffectivePolicy(dataclass): merged result
                         _merge_policies(policies) → EffectivePolicy
                           ↳ allowed_models: INTERSECTION (most restrictive = smallest set)
                           ↳ max_tokens, rpm: MINIMUM of non-None values
                         get_effective_policy(db, org_id, workspace_id, agent_group_id, agent_id)
                           ↳ single query fetching all policies matching any of the 4 levels
                         enforce_policy(policy, model, requested_max_tokens) → effective_max_tokens
                           ↳ raises AppError(message, status_code=403) if model not in allowed_models
    router.py            POST /policies

  budgets/
    models.py            Budget: id, org_id|workspace_id|agent_group_id|agent_id (exactly one set),
                         period(BudgetPeriod: DAILY|MONTHLY|TOTAL), limit_credits(BigInt),
                         auto_disable(Boolean), is_active
    service.py           _period_start(period) → datetime | None  [None for TOTAL]
                         _sum_usage_for_period(db, *, org_id|workspace_id|..., since) → int
                           ↳ walks agent hierarchy via subqueries to aggregate usage
                         check_budgets(db, org_id, workspace_id, agent_group_id, agent_id, required)
                           ↳ loads all active budgets for all 4 levels in one query
                           ↳ for each budget: compute current spend, check current+required <= limit
                           ↳ raises AppError(message, status_code=402) on any exceeded budget
    router.py            POST /budgets

  audit/
    models.py            AuditLog: id, org_id(Uuid not FK), actor_user_id(FK nullable),
                         actor_agent_id(FK nullable), event_type(String 128 indexed),
                         resource_type, resource_id, description, metadata_(JSON)
    service.py           log_event(db, org_id, event_type, *, actor_user_id, actor_agent_id,
                         resource_type, resource_id, description, metadata) → AuditLog
    [no router yet]

  gateway/
    router.py            POST /gateway/v1/chat/completions
                         Auth: "Bearer cpk_***" header
                         Body: ChatCompletionRequest(model, messages, max_tokens, temperature, stream)

                         FLOW (two separate DB transactions + one provider call):
                         Transaction 1 (pre-check, released before provider call):
                           1. resolve_api_key(hash) → ApiKey
                           2. load Agent, check status == ACTIVE
                           3. load AgentGroup, Workspace, Org (single selects)
                           4. check org.is_active, workspace.is_active, agent_group.is_active
                           5. get_effective_policy → enforce_policy (model check + token limit)
                           6. get_pricing_rule (for estimated budget pre-check)
                           7. check_budgets (estimated cost — rough pre-flight)
                           8. get_group_balance_for_update (advisory lock, actual balance check)
                         Provider call (outside transaction):
                           9. get_active_credential(db, org.id, provider_name) → byok_key or None
                          10. make_provider(name, byok_key) or get_provider(name)
                          11. provider.generate_completion(model, messages, **kwargs)
                          12. On exception: record UsageEvent(status=ERROR, credits=0) + AuditLog
                         Transaction 2 (deduct + record):
                          13. deduct_credits(group_id=org.billing_group_id, actual_credits, idem_key)
                              ↳ On InsufficientCreditsError: record BUDGET_EXCEEDED event, raise 402
                          14. Insert UsageEvent(agent_id, latency_ms, status=SUCCESS, credits_charged)
                          15. log_event(event_type="gateway.request", metadata with tokens+credits)
                         Response: OpenAI-compatible JSON + x_platform.{credits_charged, latency_ms, request_id}

                         _infer_provider(model): gpt-*/o1/o3 → openai; claude-* → anthropic;
                         mock* → mock; default → openai
```

---

## DATABASE SCHEMA (all tables)

```sql
-- Core (migration 001)
users(id UUID PK, email VARCHAR(320) UNIQUE, hashed_password VARCHAR(128), created_at)
groups(id UUID PK, name VARCHAR(255), owner_id UUID FK users, created_at)
memberships(id UUID PK, user_id FK users, group_id FK groups, role ENUM, created_at,
            UNIQUE(user_id, group_id))
ledger(id UUID PK, group_id FK groups, amount BIGINT, type ENUM, idempotency_key VARCHAR(255) UNIQUE,
       metadata JSONB, created_at)
usage_events(id UUID PK, user_id FK users, group_id FK groups, provider VARCHAR(64),
             model VARCHAR(128), input_tokens BIGINT, output_tokens BIGINT, total_tokens BIGINT,
             cost_usd NUMERIC(18,8), credits_charged BIGINT, created_at)
pricing(id UUID PK, provider VARCHAR(64), model VARCHAR(128), input_cost_per_1k NUMERIC(18,8),
        output_cost_per_1k NUMERIC(18,8), created_at, UNIQUE(provider, model))

-- Multi-tenancy additions (migration 002)
organizations(id UUID PK, name VARCHAR(255), slug VARCHAR(128) UNIQUE, owner_id FK users,
              billing_group_id FK groups, credits_per_usd INT, is_active BOOL, description TEXT, created_at)
workspaces(id UUID PK, org_id FK organizations, name VARCHAR(255), slug VARCHAR(128),
           description TEXT, is_active BOOL, created_at)
agent_groups(id UUID PK, workspace_id FK workspaces, name VARCHAR(255), description TEXT,
             is_active BOOL, created_at)
agents(id UUID PK, agent_group_id FK agent_groups, name VARCHAR(255), description TEXT,
       status ENUM('ACTIVE','DISABLED','BUDGET_EXHAUSTED'), created_at)
api_keys(id UUID PK, agent_id FK agents, name VARCHAR(255), key_hash VARCHAR(64) UNIQUE,
         key_suffix VARCHAR(8), is_active BOOL, revoked_reason TEXT, created_at)
provider_credentials(id UUID PK, org_id FK organizations, provider VARCHAR(64),
                     mode ENUM('MANAGED','BYOK'), encrypted_api_key TEXT, is_active BOOL,
                     label VARCHAR(255), created_at)
policies(id UUID PK, org_id FK orgs nullable, workspace_id FK nullable, agent_group_id FK nullable,
         agent_id FK nullable, name VARCHAR(255), allowed_models JSON, max_input_tokens INT,
         max_output_tokens INT, rpm_limit INT, is_active BOOL, created_at)
budgets(id UUID PK, org_id FK nullable, workspace_id FK nullable, agent_group_id FK nullable,
        agent_id FK nullable, period ENUM('DAILY','MONTHLY','TOTAL'), limit_credits BIGINT,
        auto_disable BOOL, is_active BOOL, created_at)
audit_logs(id UUID PK, org_id UUID, actor_user_id FK users nullable, actor_agent_id FK agents nullable,
           event_type VARCHAR(128), resource_type VARCHAR(64), resource_id VARCHAR(64),
           description TEXT, metadata JSON, created_at)

-- usage_events additions (migration 002)
ALTER TABLE usage_events ADD agent_id UUID FK agents nullable;
ALTER TABLE usage_events ADD latency_ms INT nullable;
ALTER TABLE usage_events ADD status ENUM('SUCCESS','ERROR','POLICY_BLOCKED','BUDGET_EXCEEDED') DEFAULT 'SUCCESS';
ALTER TABLE usage_events ADD error_message VARCHAR(1024) nullable;
```

---

## API ROUTES (all 32)

```
POST   /auth/register
POST   /auth/login
GET    /groups/me
POST   /groups
POST   /groups/{group_id}/invite
GET    /groups/{group_id}/balance
POST   /credits/purchase
POST   /usage/request
GET    /usage/history/{group_id}
GET    /usage/burn-rate/{group_id}
GET    /usage/top-users/{group_id}
GET    /pricing
POST   /orgs
GET    /orgs
GET    /orgs/{org_id}/balance
POST   /orgs/{org_id}/workspaces
GET    /orgs/{org_id}/workspaces
POST   /orgs/{org_id}/credentials
POST   /workspaces/{workspace_id}/agent-groups
GET    /workspaces/{workspace_id}/agent-groups
POST   /agent-groups/{agent_group_id}/agents
GET    /agent-groups/{agent_group_id}/agents
POST   /agents/{agent_id}/keys
DELETE /agents/{agent_id}/keys/{key_id}
POST   /policies
POST   /budgets
POST   /gateway/v1/chat/completions
GET    /health
GET    /docs  (Swagger UI)
GET    /redoc
GET    /openapi.json
```

---

## COMMON PATTERNS

### Adding a new domain module

```
app/<module>/
  __init__.py
  models.py      SQLAlchemy ORM (inherit UUIDMixin + TimestampMixin + Base)
  schemas.py     Pydantic v2 (model_config = {"from_attributes": True})
  service.py     async functions, accept AsyncSession
  router.py      APIRouter, use CurrentUser + DbSession dependencies
```

Then add to `app/main.py`: `app.include_router(new_router)`.

### SQLAlchemy model conventions

```python
from sqlalchemy import String, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin

class MyModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "my_table"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("parents.id"), nullable=False)
    optional_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

**NEVER use `postgresql.UUID` or `postgresql.JSONB` in models** — use portable `Uuid` and `JSON` for SQLite test compatibility.

### Raising errors

```python
from app.core.exceptions import AppError, InsufficientCreditsError, NotFoundError
raise AppError("message here", status_code=403)   # message is FIRST arg
raise InsufficientCreditsError(balance=50, required=100)  # auto 402
raise NotFoundError("Agent", str(agent_id))  # auto 404
```

### Transaction pattern in gateway

```python
async with async_session_factory() as db:
    async with db.begin():  # auto-commits on exit, rolls back on exception
        # do DB work
        await db.flush()    # send SQL but don't commit yet
    # committed here
```

### Advisory lock (balance check + deduction must share a transaction)

```python
async with db.begin():
    # Lock is released when transaction commits/rolls back
    lock_key = int(group_id.int % (2**31))
    await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))
    balance = await get_group_balance(db, group_id)
    if balance < amount:
        raise InsufficientCreditsError(balance, amount)
    await append_entry(db, group_id, -amount, TransactionType.USAGE_DEDUCTION, idem_key)
```

---

## SEEDED PRICING (scripts/seed.py)

```python
{"provider": "openai", "model": "gpt-4o",          "input": "0.0025",   "output": "0.01"}
{"provider": "openai", "model": "gpt-4o-mini",      "input": "0.000150", "output": "0.000600"}
{"provider": "openai", "model": "gpt-4-turbo",      "input": "0.01",     "output": "0.03"}
{"provider": "openai", "model": "gpt-3.5-turbo",    "input": "0.0005",   "output": "0.0015"}
{"provider": "mock",   "model": "mock-model",        "input": "0.001",    "output": "0.002"}
```

---

## TESTS (tests/)

- **conftest.py:** aiosqlite in-memory engine. `Base.metadata.create_all` — ALL models must be imported here or FK resolution fails.
- **test_ledger.py:** 6 tests. Balance computation, credit purchase, deduction, multi-transaction sum, idempotency, per-group isolation.
- **test_credit_deduction.py:** 8 tests. Token cost math, credits rounding (always ceiling), pipeline integration.
- **test_workflow.py:** 4 tests. Idempotent deduction, separate keys, refund, adjustment.
- No PostgreSQL or Temporal needed. All 18 tests pass in ~2s.

**Run:** `pipenv run test` or `make test`.

---

## DOCKER / INFRASTRUCTURE

```yaml
# docker-compose.yml — 7 services
postgres:    image: postgres:16-alpine    port: 5432
redis:       image: redis:7-alpine        port: 6379
temporal:    image: temporalio/auto-setup:1.25  port: 7234 (host) → 7233 (container)
temporal-ui: image: temporalio/ui:2.31.2  port: 8081 (host) → 8080 (container)
backend:     build: Dockerfile.backend    port: 8000
worker:      build: Dockerfile.backend    cmd: sh scripts/worker_entrypoint.sh
frontend:    build: frontend/Dockerfile   port: 3000 (host) → 80 (nginx)
```

**Why non-standard temporal port:** 7233 is in use by another project on this machine.

**Dockerfile.backend order:** `COPY . .` MUST come before `pip install -e ".[dev]"` (editable install needs source tree).

**entrypoint.sh:** Python asyncpg ping loop → `alembic upgrade head` → `python -m scripts.seed` → uvicorn.

**worker_entrypoint.sh:** Python temporalio connect loop → `python -m app.workflows.worker`.

---

## ENVIRONMENT VARIABLES

```bash
DATABASE_URL=postgresql+asyncpg://credit_platform:credit_platform_dev@postgres:5432/credit_platform
REDIS_URL=redis://redis:6379/0
TEMPORAL_HOST=temporal:7233          # inside Docker; localhost:7233 local dev
SECRET_KEY=<random 32+ bytes>
OPENAI_API_KEY=sk-...                # optional platform fallback key
CREDENTIAL_ENCRYPTION_KEY=<Fernet>  # generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDITS_PER_USD=100
```

---

## KNOWN GOTCHAS

1. **AppError argument order:** `AppError(message, status_code)` — message is first.
2. **passlib banned:** Use `bcrypt` directly (`import bcrypt`). passlib is broken on Python 3.13.
3. **No JSONB/PostgreSQL UUID in models:** Use `JSON` and `Uuid` from `sqlalchemy`. JSONB only in migrations (Alembic can target Postgres).
4. **conftest must import all models:** SQLAlchemy's `metadata.create_all` needs all table definitions visible to resolve FK dependencies.
5. **Fernet key stability:** If `CREDENTIAL_ENCRYPTION_KEY` is not set, a new key is generated per process startup. Stored credentials become permanently unreadable. Always set this in production.
6. **Advisory lock integer range:** `pg_advisory_xact_lock` takes a 64-bit signed integer. Use `int(group_id.int % (2**31))` to safely map UUID → lock key.
7. **Temporal SDK imports in workflow:** Use `workflow.unsafe.imports_passed_through()` context for non-deterministic imports (config, activities).
8. **SQLAlchemy version constraint:** Use `>=2.0.0` (not `>=2.0.36`) in pyproject.toml for Docker compatibility.

---

## FRONTEND PAGES

```
/login          LoginPage.tsx         JWT login form
/register       RegisterPage.tsx      User registration
/              DashboardPage.tsx      Balance card, burn rate, top users, recent activity
/usage         UsagePage.tsx          Legacy /usage/request form + history table
/groups        GroupsPage.tsx         Create group, purchase credits, invite member
/agents        AgentsPage.tsx         Full Org→Workspace→AgentGroup→Agent hierarchy
                                      API key issuance with reveal-once display
                                      Inline gateway test panel (fires real gateway calls)
```

**api.ts:** Typed fetch wrapper. `BASE = "/api"`. JWT token from `localStorage("token")`. All API namespaces: `authApi`, `groupsApi`, `creditsApi`, `usageApi`, `pricingApi`, `orgsApi`, `workspacesApi`, `agentGroupsApi`, `agentsApi`, `apiKeysApi`, `gatewayApi`.

**nginx.conf:** `location /api/ { proxy_pass http://backend:8000/; }` — trailing slash strips the `/api` prefix before forwarding.
