test:
	pytest -q

run-api:
	uvicorn api.main:app --reload --port 8000

run-web:
	cd web && npm run dev

build-web:
	cd web && npm run build

seed-demo:
	docker compose exec -T backend python -m scripts.seed_demo_users

demo:
	docker compose up --build

down:
	docker compose down
