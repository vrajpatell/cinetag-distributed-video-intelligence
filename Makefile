up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	echo 'alembic upgrade head'

test:
	cd backend && pytest

lint:
	cd backend && ruff check app

seed:
	python backend/app/scripts/seed_demo.py

demo: seed
