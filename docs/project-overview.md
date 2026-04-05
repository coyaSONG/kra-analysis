# 프로젝트 개요

## 한 줄 요약

이 저장소는 한국마사회(KRA) 경주 데이터를 수집하고, 경주 전 데이터를 기반으로 예측 실험과 평가를 반복하는 프로젝트입니다. 현재 운영 중심은 `apps/api`의 FastAPI 서버이고, 평가와 프롬프트 개선 실험은 `packages/scripts`에서 수행합니다.

## 현재 목표

이 프로젝트의 현재 목표는 두 가지입니다.

첫째, KRA API에서 수집한 경주 데이터를 안정적으로 저장하고 재사용 가능한 형태로 정리하는 것. 둘째, 그 데이터를 사용해 삼복연승 예측 프롬프트와 실험 파이프라인을 반복 개선하는 것입니다.

## 현재 아키텍처

실제 런타임 흐름은 아래에 가깝습니다.

```text
Client
  -> FastAPI (`apps/api/main_v2.py`)
  -> routers (`collection_v2`, `jobs_v2`, `health`, `metrics`)
  -> services (`CollectionService`, `JobService`, `KRAAPIService`)
  -> infrastructure (PostgreSQL, Redis, background tasks)
  -> KRA Public API
```

이 저장소는 모노레포이지만 현재 활성 앱은 `apps/api` 하나입니다. 예전 문서에 나오는 별도 collector 앱은 현재 워크트리에 없습니다.

## 핵심 도메인

### 1. 데이터 수집

`/api/v2/collection/` 계열 엔드포인트가 KRA API를 호출해 경주 데이터를 수집합니다. 결과는 DB에 저장되며, 일부 경로는 말/기수/조교사 상세 정보와 결과 데이터를 별도 단계로 수집합니다.

### 2. 작업 관리

`/api/v2/jobs`는 비동기 수집 작업의 상태 조회와 취소를 담당합니다. 현재 실행기는 durable queue가 아니라 API 프로세스 내부 task입니다.

### 3. 예측 평가와 프롬프트 개선

`packages/scripts/evaluation`은 평가 로직을, `packages/scripts/prompt_improvement`는 재귀 개선 로직을 담당합니다. 이 계층은 운영 API와 분리된 실험 도구입니다.

## 주요 용어

- KRA: 한국마사회.
- 삼복연승: 1, 2, 3위에 들어온 세 마리를 순서 없이 맞추는 방식.
- prerace data: 경주 결과를 알기 전 시점의 입력 데이터.
- result data: 실제 경주 결과 데이터.
- enriched data: 기본 수집 데이터에 추가 상세 정보나 파생 정보를 붙인 데이터. 현재 저장 구조와 의미는 정리 작업이 진행 중입니다.

## 현재 기술 스택

- Python 3.13+
- FastAPI
- SQLAlchemy async ORM
- PostgreSQL
- Redis
- `uv`
- `pnpm` workspace

## 현재 상태 요약

- API 엔트리포인트는 `apps/api/main_v2.py`
- 주요 라우터는 `collection_v2.py`, `jobs_v2.py`, `health.py`, `metrics.py`
- 예측/평가 실험은 `packages/scripts`
- 레거시 v1 코드(`routers/race.py`, `services/race_service.py`)는 비활성 경로

## 알려진 구조적 이슈

현재 코드베이스는 동작은 하지만 몇 가지 정리 과제를 안고 있습니다.

- Redis degrade 설계와 상세 헬스체크 구현이 완전히 일치하지 않음
- 작업 타입 vocabulary가 DB, DTO, 서비스 사이에서 분열돼 있음
- migration과 ORM 초기화가 동시에 존재해 스키마 source of truth가 불명확함
- 일부 문서가 현재 구조가 아닌 과거 구조를 설명함

이 정리 작업의 기준 문서는 [2026-03-19-architecture-remediation-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-remediation-execplan.md) 입니다.
