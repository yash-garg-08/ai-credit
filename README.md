# Multi-Tenant AI Agent Governance & Control Platform

A production-grade SaaS backend for AI agent governance, built with a modular monolith architecture. Organizations manage agents through a 4-level hierarchy, with every AI request routed through a policy-enforced proxy gateway that atomically deducts credits via an immutable ledger.

---

## What it does

| Capability | Detail |
|---|---|
| **Auth** | JWT-based register & login |
| **Multi-Tenant Hierarchy** | Platform → Organization → Workspace → AgentGroup → Agent |
| **Proxy Gateway** | OpenAI-compatible `POST /gateway/v1/chat/completions` — agents call this instead of providers directly |
| **API Key Management** | `cpk_` prefixed keys, SHA-256 hash storage (never plaintext), per-agent scoped, revocable |
| **BYOK Credentials** | Org-owned provider API keys encrypted at rest (Fernet/AES-256) |
| **Tenant Authorization** | Governance routes enforce org ownership on every create/list/mutate operation |
| **Policy Engine** | Model allowlists, per-request token limits, RPM caps — cascades from Agent → Group → Workspace → Org (most restrictive wins) |
| **Budget Enforcement** | Daily/Monthly/Total credit caps at every hierarchy level — optional auto-disable of exceeded target |
| **Immutable Ledger** | Balance = `SUM(transactions)` — never a stored balance column |
| **Temporal Workflows** | `ProcessUsageWorkflow` — idempotent credit deduction, retry-safe |
| **Multi-Provider** | OpenAI, Anthropic Claude, Mock — managed keys and BYOK supported |
| **Observability** | Latency tracking, error status, per-agent/hierarchy analytics |
| **Audit Logs** | Immutable audit trail for key creation, gateway requests, policy violations |
| **Credit Purchases** | Add credits to an org with idempotency keys |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser  :3000                         │
│  React + TypeScript + Tailwind CSS      │
│  nginx reverse-proxies /api → :8000     │
└──────────────┬──────────────────────────┘
               │ HTTP /api/*
┌──────────────▼──────────────────────────┐
│  FastAPI Backend  :8000                 │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  POST /gateway/v1/chat/         │    │
│  │  completions                    │    │
│  │                                 │    │
│  │  1. Auth cpk_ key → Agent       │    │
│  │  2. Walk hierarchy → Org        │    │
│  │  3. Policy check (model/tokens) │    │
│  │  4. Budget check (all levels)   │    │
│  │  5. Ledger balance check        │    │
│  │  6. Call Provider (BYOK/Mgd)    │    │
│  │  7. Deduct credits (atomic)     │    │
│  │  8. Record usage + audit        │    │
│  └────────────┬────────────────────┘    │
│               │                         │
│  ┌────────────▼────────────────────┐    │
│  │   Temporal Workflow Client      │    │
│  └────────────┬────────────────────┘    │
└───────────────│─────────────────────────┘
                │ gRPC
┌───────────────▼─────────────────────────┐
│  Temporal Server  :7234                 │
│  ProcessUsageWorkflow (idempotent)      │
└────────────────────────────────┬────────┘
                                 │
              ┌──────────────────▼────┐
              │  PostgreSQL  :5432    │
              │  users · orgs         │
              │  workspaces · agents  │
              │  api_keys · policies  │
              │  budgets · audit_logs │
              │  ledger · usage_events│
              │  pricing              │
              └───────────────────────┘
              ┌───────────────────────┐
              │  Redis  :6379         │
              │  (caching hook)       │
              └───────────────────────┘
```

### Entity Hierarchy

```
Organization
├── billing_group_id → groups (ledger account)
├── Workspace[]
│   └── AgentGroup[]
│       └── Agent[]
│           └── ApiKey[] (cpk_*** keys)
├── ProviderCredential[] (BYOK encrypted keys)
├── Policy[] (can apply at any level)
└── Budget[] (can apply at any level)
```

### Gateway request flow

```
Agent → POST /gateway/v1/chat/completions
         Authorization: Bearer cpk_<key>
         {model, messages, max_tokens}
         ↓
  1. SHA-256(key) → lookup api_keys → Agent
  2. Agent → AgentGroup → Workspace → Org
  3. Merge policies (model allowlist, token limits)
  4. Check budgets at all 4 levels
  5. Acquire advisory lock, check ledger balance
  6. Call provider (BYOK Fernet-decrypted key or platform key)
  7. Compute actual cost: tokens → USD → credits
  8. Deduct credits atomically (idempotency_key = request UUID)
  9. Record UsageEvent + AuditLog
 10. Return OpenAI-compatible JSON response
```

### Correctness guarantees

- **No race condition balance corruption** — PostgreSQL advisory locks held for balance-check + deduction
- **No double deduction** — Temporal workflow ID = request UUID; idempotency_key unique constraint
- **Idempotent ledger entries** — unique `idempotency_key` column prevents replay inserts
- **Credits as integers** — stored as `BIGINT` (no floating-point drift)
- **Single-target governance rules** — policy/budget target must be exactly one of org/workspace/agent_group/agent (schema + DB constraints)
- **Immutable history** — ledger rows are never updated or deleted
- **API keys never stored** — only SHA-256 hash is persisted
- **Provider credentials encrypted** — Fernet AES-256 at rest

---

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.13 · FastAPI · Uvicorn |
| ORM | SQLAlchemy 2.0 async · asyncpg |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT) · bcrypt |
| Encryption | cryptography (Fernet) for BYOK credentials |
| Workflows | Temporal Python SDK |
| HTTP client | httpx (async) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS |
| Reverse proxy | nginx |
| Containers | Docker · Docker Compose |
| Dev env | pipenv (Python) · npm (Node) |

---

## Quick start — Docker (recommended)

**Prerequisites:** Docker Desktop (or Docker Engine + Compose plugin)

```bash
git clone <repo-url>
cd ai-credit-platform

# Optional: set a Fernet encryption key for BYOK credentials
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
export CREDENTIAL_ENCRYPTION_KEY=<your-fernet-key>

# Start everything (builds images on first run)
make up

# App is ready at:
#   Frontend  →  http://localhost:3000
#   API docs  →  http://localhost:8000/docs
#   Temporal  →  http://localhost:8081
```

That's it. `make up` builds images, runs migrations (001 + 002 + 003), seeds pricing data, and starts all 7 containers.

---

## Makefile reference

```
make              Start everything (alias for make up)
make up           Build images if needed + start all containers
make build        Force-rebuild all images from scratch (no cache)
make down         Stop all containers (data volumes preserved)
make destroy      Stop containers AND wipe all volumes (resets database)
make restart      Full stop → start cycle
make logs         Tail logs for all services
make logs-backend Tail backend logs only
make logs-worker  Tail Temporal worker logs only
make ps           Show container status and ports
make health       HTTP health check for backend + frontend
make shell        Open a bash shell inside the backend container
make test         Run the Python test suite
make migrate      Run alembic migrations manually
make seed         Re-seed pricing data
make open         Open http://localhost:3000 in your browser
make clean        Remove stopped containers and dangling images
make help         Show this reference
```

---

## Local development (no Docker)

**Requirements:** Python 3.12+, pipenv, Node 20+, a running PostgreSQL + Redis + Temporal

```bash
# Backend
cp .env.example .env          # fill in DATABASE_URL, SECRET_KEY, CREDENTIAL_ENCRYPTION_KEY
pipenv install --dev
pipenv run migrate             # alembic upgrade head (runs 001, 002, 003)
pipenv run seed                # seed pricing
pipenv run dev                 # uvicorn on :8000

# Temporal worker (separate terminal)
pipenv run worker

# Frontend
cd frontend
npm install
npm run dev                    # vite dev server on :3000 (proxies /api → :8000)
```

---

## Using the Gateway

### 1. Register & create an organization

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret"}' | jq -r .access_token)

# Create org
ORG=$(curl -s -X POST http://localhost:8000/orgs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Corp"}')
ORG_ID=$(echo $ORG | jq -r .id)
GROUP_ID=$(echo $ORG | jq -r .billing_group_id)
```

### 2. Add credits

```bash
curl -X POST http://localhost:8000/credits/purchase \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"group_id\":\"$GROUP_ID\",\"amount\":10000,\"idempotency_key\":\"seed-1\"}"
```

### 3. Create the agent hierarchy

```bash
WS=$(curl -s -X POST http://localhost:8000/orgs/$ORG_ID/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production"}')
WS_ID=$(echo $WS | jq -r .id)

AG=$(curl -s -X POST http://localhost:8000/workspaces/$WS_ID/agent-groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Support Bots"}')
AG_ID=$(echo $AG | jq -r .id)

AGENT=$(curl -s -X POST http://localhost:8000/agent-groups/$AG_ID/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"support-bot-1"}')
AGENT_ID=$(echo $AGENT | jq -r .id)

KEY=$(curl -s -X POST http://localhost:8000/agents/$AGENT_ID/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"prod-key"}')
CPK=$(echo $KEY | jq -r .plaintext_key)
```

### 4. Call the gateway

```bash
curl -X POST http://localhost:8000/gateway/v1/chat/completions \
  -H "Authorization: Bearer $CPK" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"Hello!"}]}'
```

Response is OpenAI-compatible + `x_platform` billing metadata:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "mock-model",
  "choices": [{"message": {"role": "assistant", "content": "..."}}],
  "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
  "x_platform": {
    "credits_charged": 1,
    "latency_ms": 12,
    "request_id": "..."
  }
}
```

### 5. BYOK (Bring Your Own Key)

```bash
curl -X POST http://localhost:8000/orgs/$ORG_ID/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"sk-your-key","label":"prod-openai"}'
```

The gateway will automatically use this encrypted key for OpenAI requests from this org.

### 6. Policy — restrict models

```bash
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Allowlist\",\"org_id\":\"$ORG_ID\",\"allowed_models\":[\"gpt-4o-mini\",\"mock-model\"]}"
```

### 7. Budget — set a daily cap

```bash
curl -X POST http://localhost:8000/budgets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"period\":\"DAILY\",\"limit_credits\":1000,\"agent_id\":\"$AGENT_ID\"}"
```

---

## API overview

### Auth & Legacy
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET | `/groups/me` | List your legacy workspaces |
| POST | `/credits/purchase` | Add credits to a billing group |

### Multi-Tenant Hierarchy
| Method | Path | Description |
|---|---|---|
| POST | `/orgs` | Create organization |
| GET | `/orgs` | List your organizations |
| GET | `/orgs/{id}/balance` | Org credit balance |
| POST | `/orgs/{id}/workspaces` | Create workspace |
| GET | `/orgs/{id}/workspaces` | List workspaces |
| POST | `/workspaces/{id}/agent-groups` | Create agent group |
| GET | `/workspaces/{id}/agent-groups` | List agent groups |
| POST | `/agent-groups/{id}/agents` | Create agent |
| GET | `/agent-groups/{id}/agents` | List agents |
| POST | `/agents/{id}/keys` | Issue API key (returns plaintext once) |
| DELETE | `/agents/{id}/keys/{key_id}` | Revoke API key |

### Governance
| Method | Path | Description |
|---|---|---|
| POST | `/orgs/{id}/credentials` | Add BYOK provider credential |
| POST | `/policies` | Create policy rule |
| POST | `/budgets` | Create budget cap |

### AI Gateway
| Method | Path | Description |
|---|---|---|
| POST | `/gateway/v1/chat/completions` | OpenAI-compatible chat completions proxy |

### Analytics & Pricing
| Method | Path | Description |
|---|---|---|
| GET | `/usage/history/{group_id}` | Paginated usage events |
| GET | `/usage/burn-rate/{group_id}` | Credits spent 24h / 7d |
| GET | `/usage/top-users/{group_id}` | Leaderboard by spend |
| GET | `/pricing` | List all pricing rules |
| GET | `/health` | Health check |

Interactive docs: **http://localhost:8000/docs**

---

## Project structure

```
ai-credit-platform/
├── Makefile                    ← project automation
├── docker-compose.yml          ← all 7 services
├── Dockerfile.backend          ← Python app image
├── pyproject.toml              ← Python deps
├── Pipfile / Pipfile.lock      ← pipenv lockfile
├── alembic/
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_multitenancy.py
│       └── 003_single_target_constraints.py
├── app/
│   ├── main.py                 ← FastAPI app factory
│   ├── config.py               ← pydantic-settings (incl. CREDENTIAL_ENCRYPTION_KEY)
│   ├── auth/                   ← register, login, JWT
│   ├── groups/                 ← legacy workspaces (still used for billing ledger)
│   ├── ledger/                 ← immutable accounting core
│   ├── usage/                  ← events, analytics
│   ├── pricing/                ← cost engine
│   ├── providers/              ← OpenAI, Anthropic, Mock
│   ├── workflows/              ← Temporal workflow + activities + worker
│   ├── core/                   ← security, DI, exceptions
│   ├── db/                     ← SQLAlchemy engine, base models
│   │
│   ├── orgs/                   ← Organization (creates billing_group on init)
│   ├── workspaces/             ← Workspace (belongs to Org)
│   ├── agent_groups/           ← AgentGroup (belongs to Workspace)
│   ├── agents/                 ← Agent + ApiKey (cpk_ keys, SHA-256 hash)
│   ├── credentials/            ← ProviderCredential (Fernet-encrypted BYOK)
│   ├── policies/               ← Policy engine (model allowlist, token limits)
│   ├── budgets/                ← Budget caps (Daily/Monthly/Total, all levels)
│   ├── audit/                  ← Audit log (append-only)
│   └── gateway/                ← OpenAI-compatible proxy router
├── frontend/
│   ├── Dockerfile              ← node build → nginx
│   ├── nginx.conf              ← SPA + /api reverse proxy
│   └── src/
│       ├── pages/              ← Login, Register, Dashboard, Usage, Groups, Agents
│       ├── components/         ← Layout, Navbar
│       ├── context/            ← AuthContext (token, group selection)
│       └── api.ts              ← typed API client (legacy + governance APIs)
├── tests/
│   ├── test_ledger.py          ← balance, idempotency, isolation
│   ├── test_credit_deduction.py← cost engine pipeline
│   └── test_workflow.py        ← idempotency, refunds, adjustments
└── scripts/
    ├── seed.py                 ← pricing data seed
    ├── entrypoint.sh           ← backend container startup
    └── worker_entrypoint.sh    ← worker container startup
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | (postgres in compose) | asyncpg connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `TEMPORAL_HOST` | `localhost:7233` | Temporal server address |
| `SECRET_KEY` | *(change this)* | JWT signing key |
| `CREDITS_PER_USD` | `100` | Conversion rate (100 credits = $1) |
| `OPENAI_API_KEY` | *(optional)* | Platform-level OpenAI key (fallback when no BYOK) |
| `ANTHROPIC_API_KEY` | *(optional)* | Platform-level Anthropic key (fallback when no BYOK) |
| `CREDENTIAL_ENCRYPTION_KEY` | *(optional in dev)* | Fernet key for BYOK credential encryption at rest |

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy `.env.example` to `.env` and edit before running locally.

---

## Running tests

```bash
make test
# or locally:
pipenv run test
```

23 tests covering ledger correctness, governance validation/authorization, budget auto-disable, cost engine pipeline, and workflow idempotency. Tests run against an in-memory SQLite database — no running Postgres required.
