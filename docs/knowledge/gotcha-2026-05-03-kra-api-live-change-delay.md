---
title: KRA API 결과 API 라이브 변경 반영 지연
date: 2026-05-03
category: gotcha
tags: [kra-api, data-collection, live-data]
status: active
related: []
---

# KRA API 결과 API 라이브 변경 반영 지연

## Context
서울 7경주 한강캡틴 기수 변경 여부를 확인하려고 같은 시점에 2회 수집했을 때, KRA API Response에는 변경이 없었음. collection service가 호출하는 endpoint는 `API299/Race_Result_total`(결과 API) 계열.

## Gotcha
결과 API(`API299` 계열)는 **당일 라이브 변경(예: 발주 직전 기수 교체)을 반영하는 타이밍이 늦을 수 있음**. 같은 data point를 14초 간격으로 재요청해도 동일 응답이 돌아올 수 있으며, 이는 KRA API 캐싱 또는 업데이트 주기가 원인일 가능성.

더 빠른 라이브 반영이 필요하면 **출주표 전용 API(API214)** 같은 별도 endpoint 검토 필요.

## Evidence
- **테스트 시점**: 2026-05-03 경기 시작 전
- **변경 확인 대상**: 서울 7경주, 한강캡틴(chulNo 9), 기수 김철호(jkNo 080434)
- **두 수집 간격**: ~14초
- **결과**: 기수·부담중량 모두 변경 없음 (같은 응답)
- **API 계열**: API299/Race_Result_total
