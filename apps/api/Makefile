# KRA API 서버 Makefile

.PHONY: help build up down logs shell test clean migrate

# 기본 명령
help:
	@echo "사용 가능한 명령:"
	@echo "  make build       - Docker 이미지 빌드"
	@echo "  make up          - 서비스 시작 (개발 모드)"
	@echo "  make up-prod     - 서비스 시작 (프로덕션 모드)"
	@echo "  make down        - 서비스 중지"
	@echo "  make logs        - 로그 확인"
	@echo "  make shell       - API 컨테이너 쉘 접속"
	@echo "  make test        - 테스트 실행"
	@echo "  make clean       - 컨테이너 및 볼륨 삭제"
	@echo "  make migrate     - 데이터베이스 마이그레이션"

# Docker 명령
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

# 데이터베이스 명령
migrate:
	docker-compose exec api alembic upgrade head

migrate-create:
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please provide a migration message using 'make migrate-create msg=\"your message\"'"; \
		exit 1; \
	fi
	docker-compose exec api alembic revision --autogenerate -m "$(msg)"

# 테스트 명령
test:
	docker-compose exec api pytest tests/ -v

test-coverage:
	docker-compose exec api pytest tests/ --cov=. --cov-report=html

# 유틸리티 명령
clean:
	docker-compose down -v
	docker system prune -f

restart:
	$(MAKE) down
	$(MAKE) up

# 모니터링 명령
monitor-db:
	@echo "pgAdmin: http://localhost:5050"
	@echo "Use the credentials configured in your environment variables or docker-compose file"

# 환경 설정
env-setup:
	cp .env.example .env
	@echo ".env 파일이 생성되었습니다. KRA_API_KEY를 설정해주세요."