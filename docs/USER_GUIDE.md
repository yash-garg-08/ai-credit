# User Guide — AI Agent Governance & Control Platform

This guide walks you through every feature of the platform from first login to running live AI agents in production.

---

## Table of Contents

1. [Concepts](#concepts)
2. [Getting Started](#getting-started)
3. [Organizations](#organizations)
4. [Workspaces](#workspaces)
5. [Agent Groups](#agent-groups)
6. [Agents & API Keys](#agents--api-keys)
7. [Credits & Billing](#credits--billing)
8. [The AI Gateway](#the-ai-gateway)
9. [Policies — Controlling What Agents Can Do](#policies)
10. [Budgets — Controlling How Much Agents Spend](#budgets)
11. [BYOK — Bring Your Own Provider Keys](#byok)
12. [Legacy Usage API](#legacy-usage-api)
13. [Observability & Analytics](#observability--analytics)
14. [Pricing](#pricing)
15. [Administration Reference](#administration-reference)

---

## Concepts

Before you start, understand the two-track design:

### Track 1 — Governance (new)
For programmatic agent access. Agents authenticate with `cpk_` API keys and route every AI call through the gateway proxy.

```
Organization
  └── Workspace
        └── AgentGroup
              └── Agent
                    └── ApiKey (cpk_***)
```

Everything in this track is accessed at `/orgs/`, `/workspaces/`, `/agent-groups/`, `/agents/`, `/gateway/`.

### Track 2 — Legacy (original)
For direct human/UI access. Users authenticate with JWT tokens and call providers through `/usage/request`.

```
User → Group → Ledger (credits)
```

Both tracks share the same immutable credit ledger. Organizations in Track 1 get a `billing_group_id` that points into the Track 2 ledger, so credits are always consistent.

### Credits
1 USD = 100 credits (default, configurable per-org). Credits are stored as integers — no floating-point drift. Balance is always `SUM(ledger.amount)` — there is no cached balance field.

---

## Getting Started

### Option A — Docker (recommended)

```bash
git clone <repo-url>
cd ai-credit-platform
make up
```

Open `http://localhost:3000` in your browser. The API docs are at `http://localhost:8000/docs`.

### Option B — Local

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, etc.
pipenv install --dev
pipenv run migrate
pipenv run seed
pipenv run dev          # backend on :8000
pipenv run worker       # Temporal worker (separate terminal)
cd frontend && npm install && npm run dev   # frontend on :3000
```

### UI Surface Map

- `Dashboard` → group balance, burn-rate, top users, recent usage.
- `Usage` → call legacy `/usage/request`, view usage history.
- `Pricing` → backend pricing table from `/pricing`.
- `Groups & Credits` → legacy groups, invites, credit purchases.
- `Agent Governance` → org/workspace/group/agent hierarchy, org billing top-up, API key issue/list/revoke, provider credential list/create, policy list/create, budget list/create, gateway test.

---

## Organizations

An Organization is the top-level billing tenant. It owns the credit balance and all agents beneath it.
Governance APIs are owner-scoped: only the org owner can create/list/mutate resources in that org hierarchy.

### Create an organization

**UI:** Go to the **Agent Governance** page → Organizations → type a name → Create.

**API:**
```bash
curl -X POST http://localhost:8000/orgs \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "description": "Main production org"}'
```

Response:
```json
{
  "id": "org-uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "owner_id": "user-uuid",
  "billing_group_id": "group-uuid",
  "credits_per_usd": 100,
  "is_active": true,
  "created_at": "..."
}
```

The `billing_group_id` is auto-created. Use it to purchase credits (see [Credits & Billing](#credits--billing)).

### Check org balance

```bash
curl http://localhost:8000/orgs/<org_id>/balance \
  -H "Authorization: Bearer <your-jwt>"
```

---

## Workspaces

Workspaces are logical environments within an org (e.g., `production`, `staging`, `research`).

### Create a workspace

```bash
curl -X POST http://localhost:8000/orgs/<org_id>/workspaces \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production"}'
```

### List workspaces

```bash
curl http://localhost:8000/orgs/<org_id>/workspaces \
  -H "Authorization: Bearer <your-jwt>"
```

---

## Agent Groups

Agent Groups organize agents that share a purpose (e.g., `support-bots`, `data-pipeline`, `internal-tools`). Policies and budgets can be applied at the group level to govern all agents within it.

### Create an agent group

```bash
curl -X POST http://localhost:8000/workspaces/<workspace_id>/agent-groups \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Support Bots", "description": "Customer-facing agents"}'
```

---

## Agents & API Keys

An Agent is a single programmable identity. Each agent gets one or more `cpk_` API keys it uses to authenticate with the gateway.

### Create an agent

```bash
curl -X POST http://localhost:8000/agent-groups/<agent_group_id>/agents \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "support-bot-1"}'
```

### Issue an API key

```bash
curl -X POST http://localhost:8000/agents/<agent_id>/keys \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "prod-key"}'
```

Response:
```json
{
  "id": "key-uuid",
  "agent_id": "agent-uuid",
  "name": "prod-key",
  "key_suffix": "aB3xYz1k",
  "is_active": true,
  "created_at": "...",
  "plaintext_key": "cpk_M1-psPrO2tJIZc69..."
}
```

> **Important:** The `plaintext_key` is shown **exactly once** at creation. Copy it immediately. It is never stored — only a SHA-256 hash is persisted. If you lose it, revoke and reissue.

### List API keys for an agent

```bash
curl http://localhost:8000/agents/<agent_id>/keys \
  -H "Authorization: Bearer <your-jwt>"
```

### Revoke an API key

```bash
curl -X DELETE http://localhost:8000/agents/<agent_id>/keys/<key_id> \
  -H "Authorization: Bearer <your-jwt>"
```

Revocation is instant. Any in-flight request using this key will be rejected at the gateway.

### Agent statuses

| Status | Meaning |
|---|---|
| `ACTIVE` | Agent can make gateway requests |
| `DISABLED` | Manually disabled — all requests rejected |
| `BUDGET_EXHAUSTED` | Auto-disabled because a budget cap was hit |

---

## Credits & Billing

Credits power all AI requests. Both the legacy system and the governance track use the same ledger.

### Add credits to an org

Use the org's `billing_group_id` with the credits purchase endpoint:

```bash
curl -X POST http://localhost:8000/credits/purchase \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "<billing_group_id>",
    "amount": 10000,
    "idempotency_key": "topup-2026-02-27-001"
  }'
```

The `idempotency_key` prevents duplicate charges if the request is retried. Use a unique value for each top-up.

### How credits are calculated

```
cost_usd = (input_tokens / 1000) * input_price_per_1k
         + (output_tokens / 1000) * output_price_per_1k

credits = ceil(cost_usd * credits_per_usd)
```

Credits always round **up** (ceiling) to avoid under-charging. The conversion rate defaults to `credits_per_usd = 100` (100 credits = $1.00).

### Credit transaction types

| Type | Sign | When |
|---|---|---|
| `CREDIT_PURCHASE` | + | Manual top-up |
| `USAGE_DEDUCTION` | − | Successful AI request |
| `ADJUSTMENT` | ± | Manual correction |
| `REFUND` | + | Reversed charge |

---

## The AI Gateway

The gateway is the central hub for all agent AI calls. It is OpenAI API-compatible, so any code that works with the OpenAI client library works with the gateway by changing the base URL.

### Endpoint

```
POST /gateway/v1/chat/completions
Authorization: Bearer cpk_<your-api-key>
```

### Request format

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "max_tokens": 256,
  "temperature": 0.7
}
```

### Response format

```json
{
  "id": "chatcmpl-uuid",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "Paris."},
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 4,
    "total_tokens": 32
  },
  "x_platform": {
    "credits_charged": 1,
    "latency_ms": 312,
    "request_id": "uuid"
  }
}
```

The `x_platform` field is the platform's billing metadata. Your application can log it but does not need to act on it.

### What happens inside each gateway request

1. The `cpk_` key is SHA-256-hashed and looked up in the database
2. The agent's status is checked (`ACTIVE` required)
3. All policies for Agent → Group → Workspace → Org are merged; the model is validated
4. All budgets at every level are checked against current spend
5. The org's ledger balance is checked (with a PostgreSQL advisory lock)
6. The request is forwarded to the configured provider (using BYOK key if configured)
7. The actual token count is used to compute the exact cost
8. Credits are atomically deducted from the ledger
9. A `UsageEvent` and `AuditLog` entry are written
10. The OpenAI-compatible response is returned

If any step fails, the error is recorded (with `status = ERROR/POLICY_BLOCKED/BUDGET_EXCEEDED`) but you are only charged for successful completions.

### Supported models

| Provider | Example models |
|---|---|
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`, `o1`, `o3-*` |
| Anthropic | `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`, `claude-opus-4-*` |
| Mock | `mock-model` (for testing, no external calls) |

Provider is inferred from the model name. For ambiguous models, OpenAI is the default.

### Using with the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="cpk_your-agent-key",
    base_url="http://localhost:8000/gateway/v1",
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

### Error codes from the gateway

| HTTP Code | Meaning |
|---|---|
| `401` | Invalid, expired, or revoked API key |
| `402` | Insufficient credits OR budget exceeded |
| `403` | Agent disabled, org/workspace inactive, or policy violation |
| `404` | Pricing rule not found for this model |
| `502` | Provider returned an error |

---

## Policies

Policies control *what* agents are allowed to do. They cascade from the broadest (org) to the most specific (agent), and the most restrictive value always wins.

### Policy rules

| Rule | Effect |
|---|---|
| `allowed_models` | JSON array of permitted model strings. Requests for any other model are rejected with `403`. `null` = no restriction. |
| `max_input_tokens` | Maximum tokens the agent may send in a single request. The gateway enforces this before calling the provider. |
| `max_output_tokens` | Maximum tokens the provider may return. Passed as `max_tokens` to the provider. |
| `rpm_limit` | Rate limit in requests per minute (enforcement hook — requires Redis rate limiter middleware). |

### Cascade behaviour

If an org policy allows `["gpt-4o", "gpt-4o-mini"]` and a group policy allows `["gpt-4o-mini", "claude-3-haiku"]`, the effective allowed list for agents in that group is `["gpt-4o-mini"]` (intersection — most restrictive).

For numeric limits (`max_tokens`, `rpm_limit`), the minimum across all levels applies.

### Create a policy

```bash
# Restrict all agents in an org to two models
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Org model allowlist",
    "org_id": "<org_id>",
    "allowed_models": ["gpt-4o-mini", "mock-model"],
    "max_output_tokens": 2048
  }'

# Apply stricter limits to a specific agent
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent hard limit",
    "agent_id": "<agent_id>",
    "max_output_tokens": 512,
    "rpm_limit": 10
  }'
```

You must attach a policy to exactly one level: `org_id`, `workspace_id`, `agent_group_id`, or `agent_id`.
For `POST /policies`, if zero or multiple targets are provided in the payload, the API returns `422`.

### List policies for one target

```bash
curl "http://localhost:8000/policies?org_id=<org_id>" \
  -H "Authorization: Bearer <your-jwt>"
```

For `GET /policies`, provide exactly one target query parameter (`org_id`, `workspace_id`, `agent_group_id`, or `agent_id`) or the API returns `400`.

---

## Budgets

Budgets control *how much* agents spend. Like policies, they are checked at every hierarchy level before each request.

### Budget periods

| Period | Meaning |
|---|---|
| `DAILY` | Resets at midnight UTC each day |
| `MONTHLY` | Resets on the 1st of each month at midnight UTC |
| `TOTAL` | Lifetime cap — never resets |

### Create a budget

```bash
# Daily cap of 1,000 credits for a specific agent
curl -X POST http://localhost:8000/budgets \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "DAILY",
    "limit_credits": 1000,
    "auto_disable": true,
    "agent_id": "<agent_id>"
  }'

# Monthly cap of 50,000 credits across a whole workspace
curl -X POST http://localhost:8000/budgets \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "period": "MONTHLY",
    "limit_credits": 50000,
    "auto_disable": false,
    "workspace_id": "<workspace_id>"
  }'
```

Budgets must also target exactly one level (`org_id` / `workspace_id` / `agent_group_id` / `agent_id`).
For `POST /budgets`, if zero or multiple targets are provided in the payload, the API returns `422`.

### List budgets for one target

```bash
curl "http://localhost:8000/budgets?workspace_id=<workspace_id>" \
  -H "Authorization: Bearer <your-jwt>"
```

For `GET /budgets`, provide exactly one target query parameter (`org_id`, `workspace_id`, `agent_group_id`, or `agent_id`) or the API returns `400`.

When `auto_disable = true` and a budget is exhausted, the exceeded target is automatically disabled:
- `agent_id` → agent status becomes `BUDGET_EXHAUSTED`
- `agent_group_id` → agent group becomes inactive
- `workspace_id` → workspace becomes inactive
- `org_id` → organization becomes inactive

When `auto_disable = false`, the request is blocked at that moment with `402` and no target state is changed.

---

## BYOK

BYOK (Bring Your Own Key) lets each org supply its own provider API keys rather than using the platform's shared keys. Keys are encrypted with AES-256 (Fernet) before being stored. The platform never stores keys in plaintext.

### Add a BYOK credential

```bash
curl -X POST http://localhost:8000/orgs/<org_id>/credentials \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-your-openai-key",
    "label": "prod-openai-key"
  }'
```

```bash
# For Anthropic
curl -X POST http://localhost:8000/orgs/<org_id>/credentials \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "sk-ant-your-key",
    "label": "prod-anthropic-key"
  }'
```

Once a BYOK credential is active, the gateway automatically uses it for all requests from that org to that provider. If no BYOK credential exists, the platform falls back to platform-managed keys (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).

### List credentials for an org

```bash
curl http://localhost:8000/orgs/<org_id>/credentials \
  -H "Authorization: Bearer <your-jwt>"
```

### Encryption key setup

Set `CREDENTIAL_ENCRYPTION_KEY` to a Fernet key in your environment:

```bash
# Generate a key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
CREDENTIAL_ENCRYPTION_KEY=<output from above>
```

If `CREDENTIAL_ENCRYPTION_KEY` is not set, a temporary key is generated once per process startup (development only — credentials become unreadable after restart).

---

## Legacy Usage API

The original `/usage/request` endpoint remains available for direct, user-authenticated AI calls without the governance layer.

```bash
curl -X POST http://localhost:8000/usage/request \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "<group_id>",
    "provider": "mock",
    "model": "mock-model",
    "messages": [{"role": "user", "content": "Hello!"}],
    "request_id": "<uuid>"
  }'
```

This flow uses Temporal workflows for credit deduction. Use a unique `request_id` (UUID) for each call — it is the Temporal workflow ID and guarantees idempotency.

---

## Observability & Analytics

### Usage history

```bash
curl http://localhost:8000/usage/history/<group_id>?limit=50&offset=0 \
  -H "Authorization: Bearer <your-jwt>"
```

Each event includes: `provider`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `credits_charged`, `latency_ms`, `status`, `error_message`, `agent_id`, `created_at`.

### Burn rate

```bash
curl http://localhost:8000/usage/burn-rate/<group_id> \
  -H "Authorization: Bearer <your-jwt>"
```

Returns `credits_last_24h` and `credits_last_7d`.

### Top users by spend

```bash
curl http://localhost:8000/usage/top-users/<group_id>?limit=10 \
  -H "Authorization: Bearer <your-jwt>"
```

### Temporal UI

Temporal's built-in UI is available at `http://localhost:8081`. It shows every workflow execution, its history, retries, and payloads.

---

## Pricing

The pricing table drives the cost engine. All prices are in USD per 1,000 tokens.

### View current pricing

```bash
curl http://localhost:8000/pricing
```

Default seeded prices (from `scripts/seed.py`):

| Provider | Model | Input $/1k | Output $/1k |
|---|---|---|---|
| openai | gpt-4o | $0.0025 | $0.01 |
| openai | gpt-4o-mini | $0.000150 | $0.000600 |
| openai | gpt-4-turbo | $0.01 | $0.03 |
| openai | gpt-3.5-turbo | $0.0005 | $0.0015 |
| mock | mock-model | $0.001 | $0.002 |

To add a new model, insert a row into the `pricing` table or extend `scripts/seed.py`.

---

## Administration Reference

### Health check

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "2.0.0"}
```

### Container management

```bash
make up           # Start all 7 containers
make down         # Stop containers (keep data)
make destroy      # Stop and wipe all data (irreversible)
make logs         # Tail all logs
make logs-backend # Backend logs only
make ps           # Container status
make shell        # Bash inside backend container
make test         # Run test suite (SQLite, no DB required)
make migrate      # Re-run migrations
make seed         # Re-seed pricing
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL asyncpg connection string |
| `SECRET_KEY` | Yes | JWT signing key — change in production |
| `REDIS_URL` | No | Redis connection (default: `redis://localhost:6379/0`) |
| `TEMPORAL_HOST` | No | Temporal server (default: `localhost:7233`) |
| `OPENAI_API_KEY` | No | Platform-level OpenAI key (fallback if no BYOK) |
| `ANTHROPIC_API_KEY` | No | Platform-level Anthropic key (fallback if no BYOK) |
| `CREDENTIAL_ENCRYPTION_KEY` | Yes (prod) | Fernet key for BYOK encryption |
| `CREDITS_PER_USD` | No | Conversion rate (default: `100`) |

### Running tests

```bash
make test
# or
pipenv run test
```

23 tests run against an in-memory SQLite database. No running PostgreSQL or Temporal required.
