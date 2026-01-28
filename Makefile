.PHONY: help up down restart build ps logs dev lint format clean test

DOCKER_COMPOSE := docker compose
PYTHON := python3
PIP := pip3

help:
	@echo "Available commands:"
	@echo "  make up          - Start all containers"
	@echo "  make down        - Stop all containers"
	@echo "  make restart     - Restart all containers"
	@echo "  make build       - Build all container images"
	@echo "  make dev         - Start containers in development mode"
	@echo "  make ps          - Show running containers"
	@echo "  make logs        - View all container logs"
	@echo "  make logs-app    - View app container logs"
	@echo "  make shell       - Open shell in app container"
	@echo "  make test        - Run tests in container"
	@echo "  make lint        - Run linting in container"
	@echo "  make format      - Format code in container"
	@echo "  make clean       - Stop containers and clean up"
	@echo "  make rebuild     - Rebuild and restart all containers"

up:
	@echo "Starting all containers..."
	$(DOCKER_COMPOSE) up -d

down:
	@echo "Stopping all containers..."
	$(DOCKER_COMPOSE) down

restart:
	@echo "Restarting all containers..."
	$(DOCKER_COMPOSE) restart

build:
	@echo "Building all container images..."
	$(DOCKER_COMPOSE) build

rebuild: down build up
	@echo "Containers rebuilt and restarted"

dev:
	@echo "Starting containers in development mode..."
	$(DOCKER_COMPOSE) up

ps:
	@echo "Running containers:"
	$(DOCKER_COMPOSE) ps

logs:
	@echo "Tailing all container logs..."
	$(DOCKER_COMPOSE) logs -f

logs-app:
	@echo "Tailing app container logs..."
	$(DOCKER_COMPOSE) logs -f app

logs-service:
	@echo "Tailing specific service logs..."
	$(DOCKER_COMPOSE) logs -f $(SERVICE)

shell:
	@echo "Opening shell in app container..."
	$(DOCKER_COMPOSE) exec app /bin/bash

test:
	@echo "Running tests in container..."
	$(DOCKER_COMPOSE) exec app pytest tests/ -v

test-graphs:
	@echo "Testing graph implementations..."
	$(DOCKER_COMPOSE) exec app pytest tests/test_graphs/ -v

lint:
	@echo "Running linting in container..."
	$(DOCKER_COMPOSE) exec app pylint app/ || true

format:
	@echo "Formatting code in container..."
	$(DOCKER_COMPOSE) exec app black app/ tests/

format-check:
	@echo "Checking code format..."
	$(DOCKER_COMPOSE) exec app black --check app/ tests/

clean:
	@echo "Stopping containers and cleaning up..."
	$(DOCKER_COMPOSE) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ .eggs/

graph-viz:
	@echo "Generating graph visualizations..."
	$(DOCKER_COMPOSE) exec app python -c "from app.core.graphs.conversation_manager import ConversationManagerGraph; g = ConversationManagerGraph(); print(g.visualize())"

check: lint format-check
	@echo "Code checks complete"

prune:
	@echo "Pruning Docker resources..."
	docker system prune -f
	docker volume prune -f

status:
	@echo "Docker Compose Status:"
	$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "Docker Disk Usage:"
	docker system df
