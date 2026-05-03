---
title: 원격 config가 PR #7보다 최신 (30 features vs 28)
date: 2026-05-03
category: gotcha
tags: [model-config, feature-mismatch, training, pr7]
status: active
related: [discovery-2026-05-03-pr7-training-data-excluded.md]
---

# Feature Config Drift: autoresearch-pilot Has 30 Features, PR #7 Has 28

## Context
PR #7 was merged with model config featuring 28 features (`clean_model_config.json`, iter 56). However, the remote autoresearch-pilot worktree's config was updated 69 minutes before this session (2026-05-03) and now contains **30 features**, including `cancelled_count` and `field_size_live`.

## Gotcha
If anyone attempts to **train locally using this repo's code** (which expects 28 features per `clean_model_config.json`), but the training script or data schema assumes the newer 30-feature set from remote, there will be a **feature count mismatch** that blocks training. Conversely, if inference code uses the 30-feature config but the model was trained with 28, predictions will fail.

## Evidence
- Remote config location: `~/Developer/coyasong/kra-analysis-autoresearch-pilot/packages/scripts/autoresearch/clean_model_config.json`
- Updated: ~69 min before 2026-05-03 session (live field release bundle clean v2)
- Feature diff:
  ```json
  {
    "features": [
      "field_size",
      "+ cancelled_count",
      "+ field_size_live",
      "is_handicap",
      "..."
    ]
  }
  ```
- PR #7 config: 28 features, iter 56 baseline
- Code/shared modules may also have evolved to support the new features

## Implication
Before local retraining or pulling updated config from remote, verify that training data schema, `clean_model_config.json`, and inference code are all aligned on the feature count and feature names. Do not assume PR #7's iter 56 is the latest.
