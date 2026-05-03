---
title: Target Metric is set_match ≥ 0.70
date: 2026-05-03
category: decision
tags: [goals, metrics, success-criteria]
adr: docs/adr/0001-target-metric-set-match.md
status: active
related: []
---

# Target Metric: set_match ≥ 0.70

## Context
The project's foundational success criterion was initially unclear—different documents referenced different target numbers (70% "적중률" in CLAUDE.md vs set_match ≥ 0.50 in autoresearch/program.md). User clarified the canonical target as **set_match ≥ 0.70 on holdout set**.

## Decision
All architectural, feature, and optimization decisions should measure success against **set_match ≥ 0.70**. This is the holdout-set metric, not training accuracy. It supersedes prior mentions of "0.50" (which was a hard gate) and vague "70% 적중률" language.

## Evidence
- Source: User session clarification 2026-05-03
- Conflicting prior docs: `CLAUDE.md` ("70% 이상 적중률"), `packages/scripts/autoresearch/program.md` (set_match ≥ 0.50 hard gate)
- Confirmed answer: "70프로" (70%) → formalized as set_match ≥ 0.70
