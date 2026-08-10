test:
	pytest -q

run-api:
	uvicorn api.main:app --reload --port 8000

run-web:
	cd web && npm run dev

build-web:
	cd web && npm run build

seed-demo:
	docker compose run --rm backend python scripts/seed_demo_users.py

demo:
	docker compose up --build

down:
	docker compose down
