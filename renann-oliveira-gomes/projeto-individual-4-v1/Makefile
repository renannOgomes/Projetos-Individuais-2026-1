.PHONY: up down build logs cli test health

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f api

cli:
	docker-compose exec api python -m src.cli tests/fixtures/exemplo.pdf \
		--empresa "Conjuntura" --ano 2025 --trimestre 3

health:
	curl http://localhost:8000/health

test:
	docker-compose exec api pytest tests/ -v

graphql:
	@echo "GraphQL Playground: http://localhost:8000/graphql"
