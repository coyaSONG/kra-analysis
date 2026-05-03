---
title: Config version divergence (28→30 features)
date: 2026-05-03
category: discovery
tags: [model, config, version-skew, autoresearch-pilot, features]
status: active
related: []
---

# Config Version Divergence Between PR #7 and autoresearch-pilot

## Context
PR #7 merged with `clean_model_config.json` (iter 56, 28 features). However, the autoresearch-pilot environment's config file was updated 69 minutes before this session, evolved to **30 features** with new fields (`cancelled_count`, `field_size_live`).

## Finding
The remote `clean_model_config.json` is newer than PR #7's canonical version. This indicates:
- Feature definitions may be out of sync between environments
- Code/shared modules in autoresearch-pilot may have evolved beyond PR #7
- **Source of truth for features is not explicitly unified** — risk of train/inference mismatch if not reconciled

## Evidence
- Remote config timestamp: 69min before session start (lines 233-243, transcript)
- Feature diff: PR #7 = 28 fields; autoresearch-pilot = 30 fields (cancelled_count, field_size_live added)
- Note: "live field release bundle clean v2" label suggests intentional feature expansion
