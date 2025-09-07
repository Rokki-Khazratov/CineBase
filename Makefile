.PHONY: help install up down restart logs migrate makemigration db-reset fmt lint typecheck test test-e2e test-unit coverage clean shell admin

# Default target
help: ## Show this help message
	@echo "CineBase Development Commands"
	@echo "============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install dependencies
	pip install -e ".[dev]"
	pre-commit install

# Docker commands
up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View API logs
	docker-compose logs -f api

logs-db: ## View database logs
	docker-compose logs -f db

logs-redis: ## View Redis logs
	docker-compose logs -f redis

# Database commands
migrate: ## Run database migrations
	docker-compose exec api alembic upgrade head

makemigration: ## Create new migration (usage: make makemigration msg="description")
	docker-compose exec api alembic revision --autogenerate -m "$(msg)"

db-reset: ## Reset database (dev only)
	docker-compose down -v
	docker-compose up -d db redis
	sleep 5
	docker-compose exec api alembic upgrade head

db-shell: ## Connect to database shell
	docker-compose exec db psql -U cinebase -d cinebase

redis-shell: ## Connect to Redis shell
	docker-compose exec redis redis-cli

# Code quality commands
fmt: ## Format code (ruff + black + isort)
	ruff format .
	black .
	isort .

lint: ## Lint code
	ruff check .

typecheck: ## Type checking with mypy
	mypy app tests

quality: fmt lint typecheck ## Run all quality checks

# Testing commands
test: ## Run all tests
	pytest

test-e2e: ## Run E2E tests only
	pytest tests/e2e/

test-unit: ## Run unit tests only
	pytest tests/unit/

coverage: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	pytest-watch

# Utility commands
clean: ## Clean cache files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

shell: ## Open Python shell
	docker-compose exec api python

admin: ## Create admin user
	docker-compose exec api python -c "from app.services.auth_service import create_admin_user; create_admin_user()"

# Development workflow
dev-setup: install up migrate ## Complete development setup
	@echo "Development environment is ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

dev-reset: down clean up migrate ## Reset development environment
	@echo "Development environment has been reset!"

# Production commands
build: ## Build production Docker image
	docker build -t cinebase:latest .

build-prod: ## Build production image with optimizations
	docker build -f docker/Dockerfile.prod -t cinebase:prod .

# Health checks
health: ## Check service health
	@echo "Checking service health..."
	@curl -f http://localhost:8000/api/v1/health || echo "API is not responding"
	@docker-compose exec db pg_isready -U cinebase || echo "Database is not responding"
	@docker-compose exec redis redis-cli ping || echo "Redis is not responding"

# Database operations
backup: ## Create database backup
	docker-compose exec db pg_dump -U cinebase cinebase > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database from backup (usage: make restore file=backup.sql)
	docker-compose exec -T db psql -U cinebase cinebase < $(file)

# Monitoring
stats: ## Show container resource usage
	docker stats --no-stream

ps: ## Show running containers
	docker-compose ps

# Git hooks
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# Documentation
docs: ## Generate documentation
	@echo "Documentation is available at:"
	@echo "- README: README.md"
	@echo "- Development: docs/development.md"
	@echo "- Deployment: docs/deployment.md"
	@echo "- API Reference: docs/api-reference.md"
	@echo "- Architecture: architecture.md"

# Quick commands for common tasks
quick-test: fmt lint test ## Quick test (format + lint + test)

quick-dev: up migrate ## Quick development start (up + migrate)

quick-reset: down up migrate ## Quick reset (down + up + migrate)
