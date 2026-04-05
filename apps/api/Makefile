# KRA API server Makefile

.PHONY: help setup install run migrate verify-bootstrap test test-coverage \
	build up up-prod down logs shell clean restart env-setup

help:
	@echo "사용 가능한 명령:"
	@echo "  make setup             - 현재 runtime 기준 bootstrap 안내 실행"
	@echo "  make install           - Python 3.13 + uv 의존성 설치"
	@echo "  make migrate           - manifest-first DB bootstrap 실행"
	@echo "  make verify-bootstrap  - fresh DB bootstrap proof와 startup rejection 확인"
	@echo "  make run               - uvicorn main_v2:app 실행"
	@echo "  make test              - pytest 실행"
	@echo "  make test-coverage     - coverage 포함 pytest 실행"
	@echo "  make build/up/down     - 기존 docker-compose 보조 명령"
	@echo "  주의: mixed legacy/unified schema state는 fail closed 됩니다."

setup:
	bash scripts/setup.sh

install:
	uv python install 3.13
	uv sync --group dev

run:
	uv run uvicorn main_v2:app --reload --port 8000

migrate:
	uv run python3 scripts/apply_migrations.py

verify-bootstrap:
	uv run pytest -q tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''

test:
	uv run pytest tests/ -v

test-coverage:
	uv run pytest tests/ --cov=. --cov-report=html

build:
	docker-compose build

up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

up-prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec api bash

clean:
	docker-compose down -v
	docker system prune -f

restart:
	$(MAKE) down
	$(MAKE) up

env-setup:
	cp .env.template .env
	@echo ".env 파일을 생성했습니다. 실제 DATABASE_URL과 API 키를 채워 주세요."
