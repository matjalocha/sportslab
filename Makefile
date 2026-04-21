.PHONY: up down clean logs migrate test shell psql healthcheck

COMPOSE ?= docker compose
ENV_FILE ?= .env.docker

up:
	@if [ ! -f $(ENV_FILE) ]; then echo "Copy .env.docker.example to $(ENV_FILE) first"; exit 1; fi
	$(COMPOSE) --env-file $(ENV_FILE) up -d
	@echo "Waiting for postgres healthy..."
	@until $(COMPOSE) exec postgres pg_isready -U sportslab >/dev/null 2>&1; do sleep 1; done
	@echo "Stack up: API http://localhost:8000, Postgres localhost:5432, MLflow http://localhost:5000"

down:
	$(COMPOSE) down

clean:
	@read -p "Delete ALL volumes (postgres data, mlflow runs)? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=100 api

migrate:
	$(COMPOSE) exec api alembic upgrade head

test:
	$(COMPOSE) exec api pytest --cov

shell:
	$(COMPOSE) exec api bash

psql:
	$(COMPOSE) exec postgres psql -U sportslab -d sportslab

healthcheck:
	@curl -fsS http://localhost:8000/api/v1/health | python -m json.tool
