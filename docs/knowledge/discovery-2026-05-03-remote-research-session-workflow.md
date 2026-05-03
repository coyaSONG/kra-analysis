---
title: 원격 연구 세션 운영 워크플로우 (Tailscale SSH)
date: 2026-05-03
category: discovery
tags: [infrastructure, collaboration, autoresearch-pilot]
status: active
related: []
---

# 원격 연구 세션 운영 워크플로우 (Tailscale SSH)

## Context
autoresearch-pilot 검증을 진행 중인 연구용 macbook은 Tailscale VPN을 통해 SSH 접속됨. 학습 데이터와 모델을 원격에서 가져올 때 tmux 세션 간섭 없이 안전하게 파일 전송하는 방식이 필요함.

## Finding
Tailscale을 통한 SSH 접속 시 Magic DNS 비활성이면 IPv6 직접 사용. `rsync -avz`는 IPv6 brackets 파싱 실패 시 `tar over ssh` 우회 가능.

```bash
# tar 압축 전송 (IPv6 bracket 이슈 회피, 더 효율적)
ssh [user]@[host] 'tar czf - [remote_path]' | tar xzf - -C [local_path]
```

tmux pane에 직접 send-keys 하지 않으면 동시 실행 중인 codex 세션 간섭 없음.

## Evidence
- **호스트명**: chsongs-macbook-pro (Tailscale IPv6 사용)
- **원격 경로**: ~/Developer/coyasong/kra-analysis-autoresearch-pilot/packages/scripts/autoresearch/snapshots/
- **학습 데이터 파일**: full_year_2025_prerace_canonical_v2.json (60M, Apr 28 20:58:03 mtime), answer_key (80K), manifest (294K)
- **전송 방식**: tar czf over ssh (rsync IPv6 bracket 파싱 오류 우회)
