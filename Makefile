# ──────────────────────────────────────────────────────────────────────────────
# AI Credit Platform — Makefile
#
# Usage:
#   make          → same as `make up` (start everything)
#   make up       → build images if needed, start all containers
#   make build    → rebuild all images from scratch
#   make down     → stop all containers (keep volumes)
#   make destroy  → stop containers AND delete all volumes (wipes DB)
#   make restart  → stop then start
#   make logs     → tail logs for all services
#   make ps       → show running containers and ports
#   make health   → quick health check of all services
#   make test     → run the Python test suite
#   make shell    → open a shell inside the backend container
#   make clean    → remove stopped containers and dangling images
# ──────────────────────────────────────────────────────────────────────────────

COMPOSE         := docker compose
BACKEND_SVC     := backend
FRONTEND_URL    := http://localhost:3000
BACKEND_URL     := http://localhost:8000
TEMPORAL_UI_URL := http://localhost:8081

# Detect `open` (macOS) vs `xdg-open` (Linux)
OPEN := $(shell command -v open 2>/dev/null || command -v xdg-open 2>/dev/null)

.DEFAULT_GOAL := up

# ── Lifecycle ─────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Build images if needed and start all services in the background
	@echo "==> Starting AI Credit Platform…"
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  Frontend  →  $(FRONTEND_URL)"
	@echo "  Backend   →  $(BACKEND_URL)/docs"
	@echo "  Temporal  →  $(TEMPORAL_UI_URL)"
	@echo ""
	@echo "Run 'make logs' to follow logs or 'make ps' to see container status."

.PHONY: build
build: ## Force-rebuild all images (no cache)
	@echo "==> Rebuilding all images…"
	$(COMPOSE) build --no-cache

.PHONY: down
down: ## Stop all containers (data volumes are preserved)
	@echo "==> Stopping containers…"
	$(COMPOSE) down

.PHONY: destroy
destroy: ## Stop containers AND delete all volumes (database will be wiped)
	@echo "==> Destroying containers and volumes…"
	$(COMPOSE) down -v --remove-orphans
	@echo "==> All data wiped."

.PHONY: restart
restart: down up ## Full stop → start cycle

# ── Observability ─────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Tail logs for all services (Ctrl-C to exit)
	$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## Tail backend logs only
	$(COMPOSE) logs -f backend

.PHONY: logs-worker
logs-worker: ## Tail Temporal worker logs only
	$(COMPOSE) logs -f worker

.PHONY: logs-frontend
logs-frontend: ## Tail frontend (nginx) logs only
	$(COMPOSE) logs -f frontend

.PHONY: ps
ps: ## Show running containers, health, and exposed ports
	$(COMPOSE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

.PHONY: health
health: ## Quick HTTP health check against backend and frontend
	@echo "==> Backend  $(BACKEND_URL)/health"
	@curl -sf $(BACKEND_URL)/health && echo " OK" || echo " FAILED"
	@echo "==> Frontend $(FRONTEND_URL)"
	@curl -sf -o /dev/null $(FRONTEND_URL) && echo " OK" || echo " FAILED"

# ── Development helpers ───────────────────────────────────────────────────────

.PHONY: shell
shell: ## Open a bash shell inside the running backend container
	$(COMPOSE) exec $(BACKEND_SVC) bash

.PHONY: test
test: ## Run the Python test suite inside a fresh backend container
	@echo "==> Running tests…"
	$(COMPOSE) run --rm \
		-e DATABASE_URL=sqlite+aiosqlite:///:memory: \
		$(BACKEND_SVC) \
		python -m pytest tests/ -v

.PHONY: migrate
migrate: ## Run alembic migrations manually (already runs on startup)
	$(COMPOSE) exec $(BACKEND_SVC) alembic upgrade head

.PHONY: seed
seed: ## Re-seed pricing data
	$(COMPOSE) exec $(BACKEND_SVC) python -m scripts.seed

.PHONY: open
open: ## Open the app in your default browser
	@$(OPEN) $(FRONTEND_URL) || echo "Open $(FRONTEND_URL) in your browser."

# ── Maintenance ───────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove stopped containers and dangling Docker images
	@echo "==> Pruning stopped containers and dangling images…"
	docker container prune -f
	docker image prune -f

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
