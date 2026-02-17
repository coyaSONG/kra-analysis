# Legacy v1 Policy

## Scope

다음 모듈은 v1 레거시로 유지되며 활성 런타임에 포함되지 않습니다.

- `apps/api/routers/race.py`
- `apps/api/services/race_service.py`

## Active Runtime

- 활성 진입점: `apps/api/main_v2.py`
- 활성 라우터: `routers/collection_v2.py`, `routers/jobs_v2.py`
- 공개 경로: `/api/v2/collection/*`, `/api/v2/jobs/*`

## Rules

1. `main_v2.py`에 v1 라우터를 등록하지 않습니다.
2. 신규 기능은 v2 라우터/서비스에만 추가합니다.
3. 테스트/문서는 v2 기준으로 유지합니다.
4. coverage 제외는 legacy 모듈로 한정하며, 활성 모듈은 제외하지 않습니다.
