---
title: Tailscale IPv6 주소 rsync 파싱 실패와 tar-over-ssh 우회
date: 2026-05-03
category: gotcha
tags: [tailscale, ipv6, rsync, ssh, file-transfer, remote-research]
status: active
related: [discovery-2026-05-03-remote-research-session-workflow.md]
---

# Tailscale IPv6 주소 rsync 파싱 실패와 tar-over-ssh 우회

## Context
autoresearch-pilot 원격 macbook (chsongs-macbook-pro via Tailscale)에서 파일을 로컬로 가져올 때, Tailscale Magic DNS는 비활성이어서 IPv6 주소를 직접 사용해야 합니다. rsync가 IPv6 bracket 표기법(`[IPv6]:path`)을 제대로 파싱하지 못해 전송 실패합니다.

## Gotcha
`rsync -av 'coyasong@[IPv6_address]:...` 명령이 bracket 파싱 에러로 실패합니다:
```
rsync: [sender] read error: Connection reset by peer
```

Tailscale SSH는 정상 작동하지만 (사용자 `coyasong`로 확인됨), rsync는 IPv6 bracket 문법을 제대로 인식하지 못합니다. 이는 rsync 내부 URI 파서의 한계입니다.

## Solution
`tar over ssh`로 우회합니다. 압축 전송이므로 더 효율적입니다:
```bash
ssh coyasong@[IPv6_addr] 'tar czf - path/to/files' | tar xzf -
```

이 방식은 rsync보다 간단하고, IPv6 bracket 문제를 우회하며, 전송 효율도 더 좋습니다 (데이터 압축 포함).

## Evidence
- Transcript: "rsync가 IPv6 brackets 파싱에 실패했습니다. `tar over ssh`로 우회하겠습니다"
- 가져온 파일: `full_year_2025_prerace_canonical_v2.json` (60M), 3개 canonical 파일 + holdout/mini_val 검증
- Remote mtime 일치 검증으로 SSH 전송 성공 확인

## How to Apply
향후 Tailscale SSH를 통한 파일 전송이 필요할 때, rsync 대신 tar-over-ssh를 기본으로 사용하세요. 특히 원격 IP가 IPv6 형식일 때 rsync는 피하고, ssh 파이프를 통한 tar 전송으로 진행하면 파싱 문제 없이 안정적입니다.
