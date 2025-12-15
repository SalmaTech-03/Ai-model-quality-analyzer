.PHONY: run test clean docker-build

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	pytest

clean:
	rm -rf __pycache__
	rm -rf venv

docker-build:
	docker-compose build

docker-up:
	docker-compose up