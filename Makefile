.PHONY: dev demo test lint down

dev:
	docker compose up --build

demo:
	MOCK_MODE=true docker compose up --build

test:
	pytest backend/tests/ -v

lint:
	python -m compileall backend/

down:
	docker compose down
