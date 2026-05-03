---
title: 라이브 enrichment 데이터 부족으로 인한 출주마 제외
date: 2026-05-03
category: gotcha
tags: [enrichment, live-pipeline, supabase, data-starvation]
status: active
related: []
---

# 라이브 enrichment 데이터 부족으로 인한 출주마 제외

## Context
학습 데이터(2025년 1년치)는 각 마/기수/조교사의 과거 레이스 통계가 풍부하지만, 라이브 Supabase DB에는 단일 시점 스냅샷만 저장되어 있습니다. 이로 인해 enrichment 파이프라인이 라이브 경주에서 과거 통계를 찾지 못합니다.

## Gotcha
서울 7경주 12마리 중 cancelled 1마리를 제외한 **11마리가 모두 `excluded` 상태로 제외**되어 enrichment가 빈 horses 리스트를 반환합니다. 코드는 보수적으로 과거 stats가 없으면 해당 출주마를 배제하도록 설계되어 있어, 라이브 환경에서 예측 입력 데이터가 0마리 상황이 발생합니다.

학습 데이터셋은 과거 1년 누적이라 각 마/기수/조교사의 통계가 완전하지만, 라이브 API 수집 후 Supabase에 저장되는 데이터는 오늘 경주의 raw race/horse/jockey/trainer 정보만 담고 있어서 enrichment가 historical feature를 계산할 수 없게 됩니다.

## Evidence
- Transcript: "11마리: `excluded`" (사유 출력 안 됨, 정책상 제외)
- Supabase DB: live snapshot만 보관, historical stats 없음
- Train data: `full_year_2025_prerace_canonical_v2.json` 60M (과거 통계 포함)
- 메모리: enrichment_pipeline이 과거 stats 조회 실패 시 마리 제외 정책

## How to Apply
**Next step**: enrichment 파이프라인이 과거 stats를 외부 API(KRA 또는 다른 데이터 소스) 또는 로컬 캐시에서 동적으로 로드할 수 있도록 수정하거나, 라이브 경주 수집 시 과거 통계까지 사전로드하여 DB에 저장하는 방식으로 변경 필요. 현재는 라이브 예측이 완전히 차단됨.
