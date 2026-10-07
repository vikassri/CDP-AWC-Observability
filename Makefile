.PHONY: copy-kubeconfigs hub api web test

copy-kubeconfigs:
	./scripts/copy-kubeconfigs.sh

hub:
	docker compose -f deploy/docker-compose.yml up -d

api:
	PYTHONPATH=. uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8080

web:
	cd web && npm run dev

test:
	PYTHONPATH=. python -m pytest backend/tests -q
