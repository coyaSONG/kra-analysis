# Project Knowledge Index

## Decisions
- [enriched_data 파이프라인 정비 보류](decision-2026-03-15-skip-pipeline-overhaul.md) — P0~P3 보류, 피처 ablation 실험 우선

## Experiments
- [Past Top3 Stats A/B 실험](experiment-2026-03-15-past-top3-stats-ablation.md) — 최근 90일 top3 진입률이 적중률을 높이는지 검증 (실행 대기)
- [Autoresearch 휴리스틱 최적화](experiment-2026-03-15-autoresearch-heuristic-optimization.md) — 1,842경주 기반 최적화, 최종 set_match=0.640/0.667, LLM 하이브리드 실패 확인

## Discoveries
- [DB 데이터 저장 구조](discovery-2026-03-15-db-data-structure.md) — basic_data vs enriched_data 용도 차이, result_data는 top3 배열만 저장
- [구간 통과 데이터 누수](discovery-2026-03-15-sectional-data-leakage.md) — sjG1fOrd 등 27개 필드가 경주 후 데이터, FORBIDDEN 목록에 추가
- [hrDetail 동결 스냅샷](discovery-2026-03-15-hrdetail-stale-snapshot.md) — hrDetail/jkDetail/trDetail은 1회 수집 후 갱신 안 됨, 경주 결과 미반영
- [신규 KRA API 8건 통합](discovery-2026-03-15-new-api-integration.md) — collect_race_data에 6개 API 자동 통합 + collect_race_odds 신규 메서드 (API160_1/API301)
- [아키텍처 리팩터링 레거시 맵](discovery-2026-03-21-architecture-refactoring-legacy-map.md) — A~I 리팩터링 후 레거시가 된 코드 9건 식별 및 향후 작업 가이드
- [PR #7 학습 데이터 제외](discovery-2026-05-03-pr7-training-data-excluded.md) — PR #7은 추론만 포함, 학습 데이터는 autoresearch-pilot worktree에 별도 보관
- [원격 연구 세션 운영 워크플로우 (Tailscale SSH)](discovery-2026-05-03-remote-research-session-workflow.md) — autoresearch-pilot 연구용 macbook은 Tailscale VPN/SSH 접속, tar over ssh로 파일 전송

## Gotchas
- [마이그레이션 매니페스트 불일치](gotcha-2026-05-03-migration-manifest-desync.md) — 007 미등록이지만 DB에 적용, git reset이 untracked 파일 영향 안 함
- [비동기 경로 datetime 타입 미스매치](gotcha-2026-05-03-async-datetime-tz-mismatch.md) — 코드는 timezone-aware datetime, 컬럼은 WITHOUT TIME ZONE, PR #7 후 async 경로에서만 노출

## Reviews
- [Codex 리뷰: DB 구조 분석](review-2026-03-15-codex-data-analysis.md) — 초기 분석 오류 교정, 구현 플랜 검증, 4건 피드백 반영
- [GPT-5.4 Pro: 예측 전략 컨설팅](review-2026-03-15-gpt54-prediction-strategy.md) — 신규 8개 API 활용법, 피처 엔지니어링, CatBoost→triplet re-ranker 로드맵, leakage 경고
