---
title: KRA 기본 경주수 가정 문제 (15 vs 실제)
date: 2026-05-03
category: discovery
tags: [kra-api, collection, data-quality]
status: active
related: []
---

# KRA Default Race Count Assumption: 15 vs Actual Schedule

## Context
Collection logic in `collect_race_data` assumes `total_races=15` as a default for all venues. However, actual daily schedules vary: Seoul typically has 10 races, Busan varies (7 on 2026-05-03). This causes false "failed" counts in collection reports.

## Finding
On 2026-05-03:
- **Seoul**: 10 races scheduled; collection reported 10/15 with 5 "failed"
- **Busan**: 7 races scheduled; collection reported 7/15 with 8 "failed"

When queried directly against KRA API, races 8–15 returned `entries=0`, confirming those days don't have scheduled races. **The collection itself is 100% successful**, but reporting treats missing-days-not-missing-races as failures.

## Evidence
- Direct KRA API verification: `API299_Race_Result_total` returns `entries=0` for absent races
- Confirmed by user: "레이스는 10경기까지 있는게 맞아" (Seoul), "부산은 7경주까지가 맞아" (Busan on that date)
- Collection logs marked races 8–15 as "failed" despite successful 0-entry responses

## Implication
The collection counter logic should either:
1. Query the venue's actual race count **before** iterating (not assume 15)
2. Treat 0-entry responses as "not scheduled" (success) rather than failure

Current workaround: Actual data is correct; ignore false "failed" counts in reporting. Recommended for future: refine the counter logic to distinguish "no race scheduled" from "API error".
