# Project Knowledge Index

## Decisions
- [enriched_data 파이프라인 정비 보류](decision-2026-03-15-skip-pipeline-overhaul.md) — P0~P3 보류, 피처 ablation 실험 우선

## Experiments
- [Past Top3 Stats A/B 실험](experiment-2026-03-15-past-top3-stats-ablation.md) — 최근 90일 top3 진입률이 적중률을 높이는지 검증 (실행 대기)
- [Autoresearch 휴리스틱 최적화](experiment-2026-03-15-autoresearch-heuristic-optimization.md) — 1,842경주 기반 최적화, 최종 set_match=0.640/0.667, LLM 하이브리드 실패 확인

## Discoveries
- [DB 데이터 저장 구조](discovery-2026-03-15-db-data-structure.md) — basic_data vs enriched_data 용도 차이, result_data는 top3 배열만 저장
- [구간 통과 데이터 누수](discovery-2026-03-15-sectional-data-leakage.md) — sjG1fOrd 등 27개 필드가 경주 후 데이터, FORBIDDEN 목록에 추가

## Reviews
- [Codex 리뷰: DB 구조 분석](review-2026-03-15-codex-data-analysis.md) — 초기 분석 오류 교정, 구현 플랜 검증, 4건 피드백 반영
