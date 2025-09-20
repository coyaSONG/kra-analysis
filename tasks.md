# 프로젝트 작업 목록 (업데이트: 2025-09-14)

심층 분석에서 확인된 신규 이슈만 정리했습니다. 우선순위는 P0 → P1 → P2 순으로 처리하세요.

## P0 — 서비스 중단/치명적 오류
- [x] KRA API 키 누락 시 `unquote(None)` 예외를 방지하고 명확한 설정 에러 또는 대체 동작을 제공 (`apps/api/services/kra_api_service.py`, 커밋 `dc1ffe6`).
- [x] Redis 초기화 실패 시 캐시 계층이 우회하도록 `CacheService`와 종속 호출부를 방어적으로 수정 (`apps/api/infrastructure/redis_client.py`, `apps/api/services/*`, 커밋 `dc1ffe6`).

## P1 — 기능 결함/신뢰도 저하
- [x] API 키 일일 한도 계산이 날짜 경계에서 리셋되지 않는 로직 수정 (`apps/api/dependencies/auth.py`, `apps/api/tests/unit/test_auth_*`).
- [x] Collector 수집 엔드포인트 입력 검증을 통일(YYYYMMDD/meet 코드)하고 경주 번호 허용 범위를 최신 스펙(최소 15R 이상)으로 조정 (`apps/collector/src/routes/collection.ts`, `apps/collector/src/controllers/collectionController.ts`, 테스트 업데이트 포함).

## P2 — 품질 개선/운영 효율
- [x] 커버리지 제외 목록을 재검토하여 핵심 서비스·인프라 모듈을 커버리지 계산에 포함 (`apps/api/.coveragerc`).
- [x] CI 워크플로에서 린트/타입/통합 테스트 실패가 PR을 차단하도록 `|| true`, `continue-on-error` 등을 제거하고 gate를 강화 (`.github/workflows/test.yml`, `.github/workflows/code-quality.yml`).
- [x] README 등의 배지/환경 안내를 실제 리포지토리 경로와 필수 환경 변수 요구사항으로 갱신 (`README.md`).

---
완료 시 체크 후 공유해주세요. 필요하면 세분화하여 이슈/PR로 나눠 진행합니다.
