---
title: enriched와 canonical-v2 포맷의 의도적 분리
date: 2026-05-03
category: discovery
tags: [data-format, architecture, enrichment, prediction, canonical-v2]
status: active
related: []
---

# enriched와 canonical-v2 포맷의 의도적 분리

## Context
데이터 저장 포맷(enriched)과 모델 추론 포맷(canonical-v2)이 서로 다르며, 변환은 예측 시점에 메모리에서 온디맨드로 일어납니다. 이는 저장 효율성과 추론 유연성을 동시에 확보하는 아키텍처입니다.

## Finding
DB에 저장되는 enriched 형식은 수집한 raw 데이터를 강화한 형태이고, 모델 추론에 입력되는 canonical-v2 형식은 28~30개의 normalized feature set입니다. 두 포맷을 변환하는 함수는 `build_prerace_race_payload_from_enriched` (`packages/scripts/shared/prerace_prediction_payload.py:177`)이며, 이 함수는:

- **입력**: enriched race dict + race_id + race_date + meet + (선택) entry_change_notices
- **출력**: (filtered_payload, candidate_filter, field_policy, entry_change_audit) — filtered_payload가 predict 입력으로 즉시 사용 가능
- **내부 처리**: items 정규화 → 출주 후보 선별 → 금지 필드 제거 → compute_race_features로 feature 계산 → 기수 변경 상태 주석 → race_info 빌드

이 변환은 DB에 저장되지 않으며, 예측 파이프라인 실행 시점에 enriched 데이터를 읽어 메모리에서 on-the-fly로 canonical-v2로 변환합니다.

## Evidence
- `packages/scripts/shared/prerace_prediction_payload.py:177` — 변환 함수 정의
- Training data canonical-v2 포맷: 28 features (PR #7 기준)
- Remote config (2026-05-03): 30 features (cancelled_count, field_size_live 추가)
- Transcript: "enriched가 최종 DB 저장 형식이고 canonical-v2로의 변환은 추론 시점에 메모리에서 한다"

## How to Apply
새로운 feature를 추가하거나 데이터 파이프라인을 수정할 때, enriched 스키마와 canonical-v2 스키마가 분리되어 있다는 점을 기억해야 합니다. 둘 중 하나만 변경하면 불일치가 발생할 수 있습니다. 특히 DB 저장 후 충분한 시간이 지나 enriched 데이터가 누적된 후 canonical-v2 feature 정의를 변경하면, 과거 enriched 데이터는 새로운 feature 계산 규칙에 대응하지 못할 수 있습니다.
