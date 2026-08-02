up:
	docker compose up -d --build

models:
	docker compose exec ollama ollama pull qwen2:1.5b
	docker compose exec ollama ollama pull all-minilm
	docker compose exec ollama ollama pull granite3.2-vision:2b

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

test:
	cd backend && pytest

lint:
	cd backend && ruff check app

seed:
	python backend/app/scripts/seed_demo.py

demo: seed
