.PHONY: up down logs test-llm migrate

up:
	DB_PATH=./data/sqlite/siapsuhu.db docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	DB_PATH=./data/sqlite/siapsuhu.db ./scripts/migrate.sh

test-llm:
	cd llm-insight-service && python -m pytest
