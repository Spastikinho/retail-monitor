.PHONY: help build up down logs shell migrate init test lint clean

# Use docker compose (v2) instead of docker-compose (v1)
DOCKER_COMPOSE := docker compose

help:
	@echo "Retail Monitor - Makefile commands"
	@echo ""
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs (follow)"
	@echo "  make shell     - Django shell"
	@echo "  make bash      - Bash in web container"
	@echo "  make migrate   - Run migrations"
	@echo "  make init      - Initialize app (migrations + initial data + superuser)"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Run linter"
	@echo "  make clean     - Remove containers and volumes"

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

shell:
	$(DOCKER_COMPOSE) exec web python src/manage.py shell

bash:
	$(DOCKER_COMPOSE) exec web bash

migrate:
	$(DOCKER_COMPOSE) exec web python src/manage.py migrate

init:
	$(DOCKER_COMPOSE) exec web bash scripts/init.sh

test:
	$(DOCKER_COMPOSE) exec web pytest tests/ -v

lint:
	$(DOCKER_COMPOSE) exec web ruff check src/

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans

# Development shortcuts
dev-up:
	$(DOCKER_COMPOSE) up

dev-build:
	$(DOCKER_COMPOSE) build --no-cache
