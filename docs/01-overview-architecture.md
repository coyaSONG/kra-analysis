# 시스템 개요 및 아키텍처 (요약)

본 문서는 KRA 경마 데이터 분석/예측 시스템의 상위 개요와 아키텍처를 요약합니다. 자세한 기록은 `docs/_archive/`에 보관합니다.

## 목표
- 경주 데이터 수집·보강·분석·예측을 모노레포에서 일관되게 운영
- API 중심 운영(관찰 가능성, 상태 추적, 비동기 작업 관리)

## 구성 요소
- apps/api (FastAPI v2, Python 3.11+)
  - 라우터: `/api/v2/collection`, `/api/v2/jobs`
  - 미들웨어: 로깅, 레이트리밋, CORS
  - 인프라: DB/Redis/Celery 클라이언트
- apps/collector (TypeScript Node ESM)
  - KRA 공공 API 연동, 라우트/컨트롤러/서비스 계층
- packages/scripts
  - 수집·전처리·보강, 평가, 프롬프트 개선 도구

## 런타임 요약
- 포트: API 8001 (개발), Collector 3001
- 인증: `X-API-Key` (개발 기본값: `test-api-key-123456789`)
- 헬스: `/health`, `/health/detailed`

## 아키텍처 다이어그램 (개요)
```
Client → FastAPI(v2) → (Routers→Services) → PostgreSQL/Redis
                         └─ Celery(선택)
Collector(Node) ───────▶ KRA Public API
```

## 관련 문서 (보관본)
- 상세 설계/엔드포인트 시나리오: `_archive/unified-collection-api-design.md`
- 아키텍처 분석 리포트: `_archive/architectural-analysis-report.md`

