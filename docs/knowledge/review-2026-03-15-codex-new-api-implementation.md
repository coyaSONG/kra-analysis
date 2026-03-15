# Codex 리뷰: 8개 신규 API 구현

**Date:** 2026-03-15
**Category:** review
**Status:** completed
**Related files:** `apps/api/services/collection_service.py`, `apps/api/models/database_models.py`, `apps/api/services/kra_api_service.py`

## Context

8개 신규 KRA API 통합 구현 후 Codex(GPT-5.4)에 설계 리뷰 3회 + 코드 리뷰 2회 요청.

## 설계 리뷰 핵심 피드백 (3회)

### 1차 — 4건 지적
1. **P0**: enriched_data가 아닌 basic_data에 저장해야 함 → 반영
2. **P1**: API11_1을 jkDetail에 병합하면 필드 충돌 → jkStats 분리로 반영
3. **P1**: race_odds에 UNIQUE + UPSERT 전략 누락 → 반영
4. **P2**: 파티셔닝 불필요, 복합 인덱스만 → 반영

### 2차 — 4건 추가 지적
1. race_odds 인덱스에 source 누락 → `idx_race_odds_date_pool_source` 반영
2. training 매칭이 hrName 기반 → 설계 문서에 hrNo 권장 명시
3. pool/source가 자유 텍스트 → CHECK 제약 추가
4. CREATE POLICY 재실행 시 실패 → DROP IF EXISTS 패턴 반영

### 3차 — 통과
- 파이프라인 섹션 API329 설명 통일 후 자기모순 해소 확인

## 코드 리뷰 핵심 피드백 (2회)

### 1차 — 4건 지적
1. **meet 미전달**: `get_jockey_stats`/`get_owner_info`에 meet 안 넘겨서 항상 서울("1")로 조회 → `_collect_horse_details`에 meet 파라미터 추가
2. **training hrName 매칭**: 설계는 hrNo 기반인데 구현은 hrName → API329에 hrNo 미제공이라 hrName 유지 + unmatched 로깅 추가
3. **RaceOdds 모델 CHECK 누락**: migration에만 CHECK 있고 모델엔 없음 → `CheckConstraint` 추가
4. **collect_race_odds rollback 없음**: source 검증 + try/except/rollback 추가

### 2차 — 1건 추가 지적
- `horse_basic.get("meet")`가 문자열("서울")일 수 있음 → `collect_race_data`의 정수 meet를 직접 전달하도록 수정 → 통과

## Impact

- Codex 리뷰를 통해 설계 단계에서 5건, 구현 단계에서 5건의 버그/불일치를 사전 발견
- 특히 meet 미전달 버그는 부산/제주 경주에서 잘못된 데이터가 저장되는 심각한 버그였음
- CheckConstraint 누락은 로컬/테스트 환경에서만 잘못된 값이 허용되는 환경 불일치 문제
