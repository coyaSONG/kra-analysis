# Second Brain Vault Design Spec

**Date:** 2026-03-19
**Status:** Approved
**Vault Path:** `~/Documents/second-brain`

---

## 1. Overview

Obsidian + Claude Code 기반 Second Brain 시스템 구축.
개인 지식 관리(PKM) + KRA 경마 분석 프로젝트 관리를 통합하는 풀 스타터킷.

**핵심 구성:**
- PARA 폴더 구조 + 목표 캐스케이드
- 커스텀 스킬 6개 + kepano 공식 스킬 5개
- Git hooks 자동 커밋
- .base 대시보드 3종
- 타입별 Frontmatter 표준 스키마

**핵심 규칙:**
- `type` frontmatter 필드는 모든 노트에 필수. 대시보드, 스킬, 검색 모두 이 필드에 의존.
- `/vault-review` 스킬이 `type` 누락 노트를 감지하여 경고.

---

## 2. Folder Structure

```
~/Documents/second-brain/
├── CLAUDE.md
├── .claude/
│   ├── skills/
│   │   ├── daily/SKILL.md
│   │   ├── weekly/SKILL.md
│   │   ├── monthly/SKILL.md
│   │   ├── inbox-processor/SKILL.md
│   │   ├── vault-review/SKILL.md
│   │   └── braindump/SKILL.md
│   └── settings.json
├── 00_Inbox/
│   └── index.md
├── 01_Projects/
│   ├── index.md
│   └── KRA Analysis/
├── 02_Areas/
│   ├── index.md
│   ├── Career/
│   ├── Health/
│   └── Finance/
├── 03_Resources/
│   ├── index.md
│   ├── Books/
│   ├── Articles/
│   └── People/
├── 04_Archive/
│   └── index.md
├── 05_Attachments/
├── Daily/
├── Weekly/
├── Goals/
│   ├── vision-2024-2026.md
│   ├── yearly-2026.md
│   ├── quarterly-2026-Q1.md
│   └── monthly-2026-03.md
├── Templates/
│   ├── daily.md
│   ├── project.md
│   ├── book.md
│   ├── article.md
│   └── person.md
├── Bases/
│   ├── projects.base
│   ├── reading-list.base
│   └── daily-index.base
└── tasks.md
```

### tasks.md

중앙 태스크 목록. `/daily` 스킬이 여기서 미완료 태스크를 읽고, `/inbox` 스킬이 실행 가능한 항목을 여기에 추가한다.

```markdown
# Tasks

## Active
- [ ] #project/kra 모델 v3 학습 데이터 정리
- [ ] #area/health 주 3회 운동 루틴 시작

## Someday
- [ ] Obsidian 플러그인 개발 시도
```

---

## 3. Goal Cascade System

```
3-Year Vision → Yearly Goals → Quarterly → Monthly → Weekly Review → Daily Tasks
```

- `Goals/vision-2024-2026.md` — 3년 비전 (큰 방향성)
- `Goals/yearly-2026.md` — 연간 목표 3-5개, 비전에 `[[link]]`
- `Goals/quarterly-2026-Q1.md` — 분기 마일스톤, 연간 목표에 `[[link]]`
- `Goals/monthly-2026-03.md` — 월간 구체 목표, 분기에 `[[link]]`
- `Weekly/weekly-2026-W12.md` — `/weekly` 스킬이 `Weekly/` 폴더에 생성, 월간에 연결
- `Daily/2026-03-19.md` — `/daily` 스킬이 주간에서 Top 3 표면화
- 활성 프로젝트가 연결된 목표가 없으면 경고하는 감사 기능 포함

---

## 4. Skills (6 Custom + 5 Official)

### 4.1 Custom Skills

| Skill | Trigger | Behavior |
|-------|---------|----------|
| `/daily` | 아침/저녁 | 어제 미완료 확인 → OKR 정렬 → Top 3 추천 (아침) / 성과·블로커 추출 → 이월 처리 (저녁) |
| `/weekly` | 일요일 | `Weekly/weekly-YYYY-WXX.md` 생성, 주간 프로젝트 롤업, 목표 진척도, 다음 주 포커스 설정 |
| `/monthly` | 월말 | 월간 리뷰, 분기 마일스톤 체크, 목표 재조정 |
| `/inbox` | 수시 | Inbox 노트 순회 → 엔티티 추출 → `[[wikilink]]` → 올바른 폴더 분류 → index.md 업데이트 |
| `/vault-review` | 수시 | 고아 노트, 깨진 링크, 중복, frontmatter `type` 누락, stale inbox 탐지 |
| `/braindump` | 수시 | `$ARGUMENTS` 내용을 Inbox에 저장 + 자동 태깅 + 관련 노트 제안 |

### 4.2 Official Skills (kepano/obsidian-skills)

| Skill | Purpose |
|-------|---------|
| `obsidian-markdown` | Obsidian 문법 규칙 보장 |
| `obsidian-bases` | .base 대시보드 작성 규칙 |
| `obsidian-cli` | CLI로 vault 상호작용 |
| `json-canvas` | 시각적 캔버스 생성 |
| `defuddle` | 웹 클리핑 시 클린 마크다운 추출 |

---

## 5. Hooks

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd $(git rev-parse --show-toplevel) && git add -A && git commit -m \"checkpoint: $(date +%H:%M) $(git diff --cached --name-only | head -1)\""
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[Second Brain] 활성 프로젝트, 미처리 inbox, 마지막 리뷰 이후 일수를 확인하세요\""
          }
        ]
      }
    ]
  }
}
```

---

## 6. Frontmatter Schema

모든 노트에 `type` 필드 필수. 이 필드가 없으면 대시보드에 표시되지 않으며, `/vault-review`가 경고한다.

### Daily Note
```yaml
---
type: daily
date: 2026-03-19
week: "[[weekly-2026-W12]]"
energy: 7
---
```

### Weekly Review
```yaml
---
type: weekly
week: 2026-W12
month: "[[monthly-2026-03]]"
---
```

### Project
```yaml
---
type: project
status: active
goal: "[[yearly-2026]]"
start: 2026-03-01
due: 2026-06-30
tags: [kra, ml]
---
```

### Book
```yaml
---
type: book
title: ""
author: ""
rating: 0
status: to-read
tags: []
---
```

### Article
```yaml
---
type: article
title: ""
author: ""
source: ""
status: to-read
tags: []
---
```

### Person
```yaml
---
type: person
role: ""
org: ""
tags: [people]
---
```

---

## 7. Base Dashboards

### projects.base
```yaml
filters:
  and:
    - file.inFolder("01_Projects")
    - 'status != "done"'
formulas:
  days_active: 'if(start, (now() - date(start)).days, (now() - file.ctime).days)'
  goal_link: 'if(goal, goal, "미연결")'
views:
  - type: table
    name: "Active Projects"
    order: [file.name, status, formula.goal_link, due, formula.days_active]
```

### reading-list.base
```yaml
filters:
  or:
    - 'type == "book"'
    - 'type == "article"'
formulas:
  status_icon: 'if(status == "reading", "📖", if(status == "done", "✅", "📚"))'
views:
  - type: cards
    name: "Library"
    order: [file.name, author, formula.status_icon, rating]
```

### daily-index.base
```yaml
filters:
  and:
    - 'type == "daily"'
    - '/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)'
formulas:
  day_of_week: 'if(date, date(date).format("dddd"), "")'
views:
  - type: table
    name: "Recent Days"
    limit: 14
    order: [file.name, formula.day_of_week, energy]
```

---

## 8. Templates

### daily.md
```markdown
---
type: daily
date: {{date}}
week: "[[weekly-{{week}}]]"
energy:
---

## Top 3 Goals
1.
2.
3.

## Notes


## Log


## Reflection
- 오늘 잘한 것:
- 내일 개선할 것:
```

### project.md
```markdown
---
type: project
status: active
goal:
start: {{date}}
due:
tags: []
---

## Objective


## Tasks
- [ ]

## Log

## References
```

### book.md
```markdown
---
type: book
title: ""
author: ""
rating:
status: to-read
tags: []
---

## Summary


## Key Takeaways
1.

## Quotes

## Notes
```

### article.md
```markdown
---
type: article
title: ""
author: ""
source: ""
status: to-read
tags: []
---

## Summary


## Key Points


## Notes
```

### person.md
```markdown
---
type: person
role: ""
org: ""
tags: [people]
---

## Context


## Notes


## Meetings
```

---

## 9. CLAUDE.md

```markdown
# Second Brain

이것은 개인 지식 관리 + 프로젝트 관리 볼트입니다.
Claude Code가 이 파일들을 운영합니다.

## Structure
- 00_Inbox/ -- 미처리 원시 캡처, 브레인덤프
- 01_Projects/ -- 명확한 결과물이 있는 활성 작업
- 02_Areas/ -- 지속적 책임 영역
- 03_Resources/ -- 참조 자료 (Books/, Articles/, People/)
- 04_Archive/ -- 완료 또는 비활성
- 05_Attachments/ -- 이미지, PDF 등 미디어
- Daily/ -- 일일 노트 (YYYY-MM-DD.md)
- Weekly/ -- 주간 리뷰 (weekly-YYYY-WXX.md)
- Goals/ -- 목표 캐스케이드 (vision, yearly, quarterly, monthly)
- tasks.md -- 중앙 태스크 목록

## Conventions
- 모든 노트에 `type` frontmatter 필수 (daily, weekly, project, book, article, person)
- [[wikilinks]]를 볼트 내 노트에 사용, [text](url)은 외부 URL에만
- 태그는 #category/subcategory 형식
- 날짜는 YYYY-MM-DD 표준
- 모든 폴더에 index.md 유지 (볼트 탐색 지도)

## What NOT To Do
- 명시적 요청 없이 파일 생성하지 않음
- 폴더 계층 재구조화하지 않음
- 기존 노트 내용 임의 수정하지 않음
- 이모지 추가하지 않음

## Templates
- Templates/ 폴더의 템플릿을 사용하여 새 노트 생성
- 각 타입별 frontmatter 스키마 준수

## Active Context
- 현재 프로젝트: KRA 경마 데이터 분석 (70% 적중률 목표)
```

---

## 10. Git Integration

- vault를 git repo로 초기화
- Hooks로 자동 커밋 → 모든 변경 추적
- 대규모 변경은 별도 브랜치에서 PR 형태로 검토 가능

### .gitignore
```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/*/data.json
.trash/
.DS_Store
```
