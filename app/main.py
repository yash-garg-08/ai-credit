from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent_groups.router import router as agent_groups_router
from app.agents.router import key_router, router as agents_router
from app.auth.router import router as auth_router
from app.budgets.router import router as budgets_router
from app.core.exceptions import AppError
from app.credentials.router import router as credentials_router
from app.db.session import engine
from app.gateway.router import router as gateway_router
from app.groups.router import router as groups_router
from app.ledger.router import router as ledger_router
from app.orgs.router import router as orgs_router
from app.policies.router import router as policies_router
from app.pricing.router import router as pricing_router
from app.providers.registry import close_all as close_providers
from app.usage.router import router as usage_router
from app.workspaces.router import router as workspaces_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_providers()
    await engine.dispose()


app = FastAPI(
    title="AI Agent Governance & Control Platform",
    version="2.0.0",
    description="Multi-tenant AI agent governance with proxy gateway, policy engine, budget enforcement, and BYOK credentials.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# ── Legacy routes (v1 groups/ledger/usage) ───────────────────────────────────
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(ledger_router)
app.include_router(usage_router)
app.include_router(pricing_router)

# ── Multi-tenant hierarchy ────────────────────────────────────────────────────
app.include_router(orgs_router)
app.include_router(workspaces_router)
app.include_router(agent_groups_router)
app.include_router(agents_router)
app.include_router(key_router)

# ── Governance ────────────────────────────────────────────────────────────────
app.include_router(credentials_router)
app.include_router(policies_router)
app.include_router(budgets_router)

# ── AI Proxy Gateway ──────────────────────────────────────────────────────────
app.include_router(gateway_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}
