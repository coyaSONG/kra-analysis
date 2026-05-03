---
title: PR #7 intentionally excluded training dataset
date: 2026-05-03
category: discovery
tags: [pr7, model, scope, training-data]
status: active
related: []
---

# PR #7 Training Data Exclusion

## Context
PR #7 brought the inference pipeline to main (predict endpoint, autoresearch modules, shared services), but deliberately excluded all training datasets to keep the PR bounded and reviewable.

## Finding
Training data lives in `autoresearch-pilot` worktree, not in main:
```
~/Developer/Personal/kra-analysis-autoresearch-pilot/
  packages/scripts/autoresearch/snapshots/
    - full_year_2025_prerace_canonical_v2.json (16,146 rows)
    - full_year_2025_prerace_canonical_v2_answer_key.json
    - full_year_2025_prerace_canonical_v2_manifest.json
```

What PR #7 **included**:
- ✓ autoresearch modules (24), shared modules (30)
- ✓ `train_clean.py`, `predict_clean.py` CLI
- ✓ predict endpoint + service
- ✓ `clean_model_config.json` (iter 56 champion config)
- ✓ data contracts (7 CSV schemas)

What PR #7 **excluded**:
- ✗ training snapshots (57MB+ canonical_v2.json family)
- ✗ trained joblib models

This means retraining or model updates require manually fetching data from the autoresearch-pilot worktree.

## Evidence
- PR #7 description explicitly states: "추론에 필요한 인프라만 포함. 학습 dataset snapshot(57MB canonical_v2.json 외 7개)은 commit 제외."
- Current state: `champion_clean.joblib` not in models/ (PR #7 caveat still in effect)
- Training data location: autoresearch-pilot separate worktree

