test:
	pytest -q

run-api:
	uvicorn api.main:app --reload --port 8000

run-web:
	cd web && npm run dev

build-web:
	cd web && npm run build

# Target `demo` ditambahkan HANYA setelah docker-compose.yml ada dan diuji.
# Jangan mencantumkan perintah yang diketahui gagal.
