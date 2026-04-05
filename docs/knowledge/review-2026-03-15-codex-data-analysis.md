# Codex(GPT-5.4) 리뷰 — DB 구조 및 수정 방향

**Date:** 2026-03-15
**Category:** review
**Status:** completed
**Related files:** `apps/api/services/collection_service.py`, `packages/scripts/shared/db_client.py`

## Context

Supabase DB의 데이터 저장 구조를 분석한 후, Claude의 초기 분석("데이터가 잘못된 곳에 저장됨")이 정확한지 Codex(GPT-5.4, tmux pane 2:1.2)에 리뷰 요청.

## Key Feedback

### 1차 리뷰: 초기 분석 검증

Claude의 분석 중 **2번, 3번은 정확**, **1번, 4번은 수정 필요**로 판정:

- **수정 1**: hrDetail/jkDetail/trDetail은 "잘못 저장된 enriched 데이터"가 아니라, 수집 단계 산출물로 basic_data에 포함되는 게 설계 의도
- **수정 2**: "데이터 손실 없음"은 과장 — 1,575건에서 부분 상세 누락, 1건 빈 horses

### 2차 리뷰: 수정 방향 제안

P0~P3 우선순위 체계 제안 (상세: `decision-2026-03-15-skip-pipeline-overhaul.md`)

### 3차 리뷰: 현실적 조언

**핵심 메시지**: "지금은 데이터 아키텍처를 예쁘게 만드는 단계가 아니라, 어떤 피처가 적중률을 올리는지 빨리 증명하는 단계"
- P0~P3 전부 하는 건 과함
- ablation 실험 우선 추천
- enriched_data 파이프라인은 피처 효과 입증 후에만 투자

### 4차 리뷰: 구현 플랜 검증

past_stats 구현 플랜에서 발견한 문제 4건:
1. 테스트 mock에서 `_conn.closed` 미설정 → 실제 DB 연결 시도 가능
2. SQL에 `result_status = 'collected'` 필터 누락
3. 테스트 파일에 `sys.path.insert()` 누락
4. 기권마(`win_odds == 0`) 필터 없음 → top3율 과소추정 가능

## Actions Taken

- 4건 모두 구현에 반영
- `result_data` 문자열 파싱 방어 코드 추가
- `hr_nos` 중복 제거(`set()`) 추가
- `top3[0]` 접근 전 빈 리스트 체크 추가

## Impact

- Codex를 코드 리뷰어로 활용하는 패턴이 효과적임을 확인
- 특히 데이터 타입/구조 검증, 엣지케이스 발견에 강점
