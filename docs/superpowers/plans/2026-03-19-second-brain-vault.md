# Second Brain Vault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Obsidian + Claude Code 기반 Second Brain vault를 `~/Documents/second-brain`에 구축한다.

**Architecture:** PARA 폴더 구조 + 목표 캐스케이드 + 커스텀 스킬 6개 + kepano 공식 스킬 5개 + .base 대시보드 3종. Git으로 버전 관리하며, Claude Code hooks로 자동 커밋.

**Tech Stack:** Obsidian, Claude Code Skills (SKILL.md), YAML (.base), Git

**Spec:** `docs/superpowers/specs/2026-03-19-second-brain-vault-design.md`

---

## File Structure

```
~/Documents/second-brain/
├── CLAUDE.md
├── .gitignore
├── .claude/
│   ├── settings.json
│   └── skills/
│       ├── daily/SKILL.md
│       ├── weekly/SKILL.md
│       ├── monthly/SKILL.md
│       ├── inbox-processor/SKILL.md
│       ├── vault-review/SKILL.md
│       └── braindump/SKILL.md
├── 00_Inbox/index.md
├── 01_Projects/index.md
├── 01_Projects/KRA Analysis/index.md
├── 02_Areas/index.md
├── 03_Resources/index.md
├── 04_Archive/index.md
├── Daily/            (empty, populated by /daily skill)
├── Weekly/           (empty, populated by /weekly skill)
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

---

### Task 1: Vault 디렉토리 + Git 초기화

**Files:**
- Create: `~/Documents/second-brain/`
- Create: `~/Documents/second-brain/.gitignore`

- [ ] **Step 1: Vault 루트 디렉토리 생성**

```bash
mkdir -p ~/Documents/second-brain
```

- [ ] **Step 2: Git 초기화**

```bash
cd ~/Documents/second-brain && git init
```

- [ ] **Step 3: .gitignore 작성**

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/*/data.json
.trash/
.DS_Store
```

- [ ] **Step 4: 초기 커밋**

```bash
cd ~/Documents/second-brain
git add .gitignore
git commit -m "init: second-brain vault"
```

---

### Task 2: PARA 폴더 구조 + index.md

**Files:**
- Create: `00_Inbox/index.md`
- Create: `01_Projects/index.md`
- Create: `01_Projects/KRA Analysis/index.md`
- Create: `02_Areas/index.md`
- Create: `03_Resources/index.md`
- Create: `04_Archive/index.md`
- Create: `05_Attachments/` (empty dir)
- Create: `Daily/` (empty dir)
- Create: `Weekly/` (empty dir)

- [ ] **Step 1: PARA 폴더 생성**

```bash
cd ~/Documents/second-brain
mkdir -p 00_Inbox 01_Projects/KRA\ Analysis 02_Areas/Career 02_Areas/Health 02_Areas/Finance 03_Resources/Books 03_Resources/Articles 03_Resources/People 04_Archive 05_Attachments Daily Weekly
```

- [ ] **Step 2: 00_Inbox/index.md 작성**

```markdown
---
type: index
---

# Inbox

미처리 캡처, 브레인덤프, 빠른 메모가 여기에 들어옵니다.
`/inbox` 스킬로 정리하세요.

## Contents
```

- [ ] **Step 3: 01_Projects/index.md 작성**

```markdown
---
type: index
---

# Projects

시간 한정 프로젝트. 명확한 결과물과 마감이 있는 작업.

## Active
- [[KRA Analysis]]
```

- [ ] **Step 4: 01_Projects/KRA Analysis/index.md 작성**

```markdown
---
type: project
status: active
goal: "[[yearly-2026]]"
start: 2025-06-01
due: 2026-12-31
tags: [kra, ml]
---

# KRA Analysis

한국마사회 경마 데이터 분석 — 삼복연승(1-3위) 예측 AI 시스템 개발.
목표: 70% 이상 적중률.

## Tasks
- [ ] 모델 v3 학습 데이터 정리
- [ ] Feature engineering 확장

## Log

## References
- [[../../docs/project-overview.md|프로젝트 개요]]
```

- [ ] **Step 5: 02_Areas/index.md 작성**

```markdown
---
type: index
---

# Areas

지속적으로 관리하는 책임 영역.

## Active Areas
- [[Career]]
- [[Health]]
- [[Finance]]
```

- [ ] **Step 6: 03_Resources/index.md 작성**

```markdown
---
type: index
---

# Resources

참조 자료, 에버그린 콘텐츠.

## Categories
- [[Books]]
- [[Articles]]
- [[People]]
```

- [ ] **Step 7: 04_Archive/index.md 작성**

```markdown
---
type: index
---

# Archive

완료되었거나 더 이상 활성화되지 않은 항목.

## Contents
```

- [ ] **Step 8: 하위 폴더 index.md 작성 (Areas + Resources)**

`02_Areas/Career/index.md`, `02_Areas/Health/index.md`, `02_Areas/Finance/index.md`, `03_Resources/Books/index.md`, `03_Resources/Articles/index.md`, `03_Resources/People/index.md` 각각 동일 패턴:

```markdown
---
type: index
---

# {Folder Name}

## Contents
```

- [ ] **Step 9: .gitkeep 추가 (빈 폴더 유지)**

```bash
cd ~/Documents/second-brain
touch 05_Attachments/.gitkeep Daily/.gitkeep Weekly/.gitkeep
```

- [ ] **Step 10: 커밋**

```bash
cd ~/Documents/second-brain
git add -A
git commit -m "feat: add PARA folder structure with index files"
```

---

### Task 3: 목표 캐스케이드 파일

**Files:**
- Create: `Goals/vision-2024-2026.md`
- Create: `Goals/yearly-2026.md`
- Create: `Goals/quarterly-2026-Q1.md`
- Create: `Goals/monthly-2026-03.md`

- [ ] **Step 1: Goals 폴더 생성**

```bash
mkdir -p ~/Documents/second-brain/Goals
```

- [ ] **Step 2: vision-2024-2026.md 작성**

```markdown
---
type: vision
period: 2024-2026
---

# 3-Year Vision (2024-2026)

## Big Picture


## Core Values


## Success Looks Like
```

- [ ] **Step 3: yearly-2026.md 작성**

```markdown
---
type: yearly
year: 2026
vision: "[[vision-2024-2026]]"
---

# 2026 Yearly Goals

## Goals
1. KRA 예측 모델 70% 적중률 달성
2.
3.

## Review
- Q1:
- Q2:
- Q3:
- Q4:
```

- [ ] **Step 4: quarterly-2026-Q1.md 작성**

```markdown
---
type: quarterly
quarter: 2026-Q1
yearly: "[[yearly-2026]]"
---

# 2026 Q1 Milestones

## Milestones
1.

## Progress
- Month 1:
- Month 2:
- Month 3:
```

- [ ] **Step 5: monthly-2026-03.md 작성**

```markdown
---
type: monthly
month: 2026-03
quarterly: "[[quarterly-2026-Q1]]"
---

# 2026-03 Monthly Goals

## Goals
1.

## Weekly Progress
- W10:
- W11:
- W12:
- W13:
```

- [ ] **Step 6: 커밋**

```bash
cd ~/Documents/second-brain
git add Goals/
git commit -m "feat: add goal cascade files (vision, yearly, quarterly, monthly)"
```

---

### Task 4: Templates

**Files:**
- Create: `Templates/daily.md`
- Create: `Templates/project.md`
- Create: `Templates/book.md`
- Create: `Templates/article.md`
- Create: `Templates/person.md`

- [ ] **Step 1: Templates 폴더 생성**

```bash
mkdir -p ~/Documents/second-brain/Templates
```

- [ ] **Step 2: daily.md 작성**

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

- [ ] **Step 3: project.md 작성**

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

- [ ] **Step 4: book.md 작성**

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

- [ ] **Step 5: article.md 작성**

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

- [ ] **Step 6: person.md 작성**

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

- [ ] **Step 7: 커밋**

```bash
cd ~/Documents/second-brain
git add Templates/
git commit -m "feat: add 5 note templates (daily, project, book, article, person)"
```

---

### Task 5: .base 대시보드

**Files:**
- Create: `Bases/projects.base`
- Create: `Bases/reading-list.base`
- Create: `Bases/daily-index.base`

- [ ] **Step 1: Bases 폴더 생성**

```bash
mkdir -p ~/Documents/second-brain/Bases
```

- [ ] **Step 2: projects.base 작성**

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

- [ ] **Step 3: reading-list.base 작성**

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

- [ ] **Step 4: daily-index.base 작성**

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

- [ ] **Step 5: 커밋**

```bash
cd ~/Documents/second-brain
git add Bases/
git commit -m "feat: add 3 base dashboards (projects, reading-list, daily-index)"
```

---

### Task 6: tasks.md

**Files:**
- Create: `tasks.md`

- [ ] **Step 1: tasks.md 작성**

```markdown
# Tasks

## Active
- [ ] #project/kra 모델 v3 학습 데이터 정리
- [ ] #area/health 주 3회 운동 루틴 시작

## Someday
- [ ] Obsidian 플러그인 개발 시도
```

- [ ] **Step 2: 커밋**

```bash
cd ~/Documents/second-brain
git add tasks.md
git commit -m "feat: add central tasks file"
```

---

### Task 7: Custom Skills (6개)

**Files:**
- Create: `.claude/skills/daily/SKILL.md`
- Create: `.claude/skills/weekly/SKILL.md`
- Create: `.claude/skills/monthly/SKILL.md`
- Create: `.claude/skills/inbox-processor/SKILL.md`
- Create: `.claude/skills/vault-review/SKILL.md`
- Create: `.claude/skills/braindump/SKILL.md`

- [ ] **Step 1: skills 디렉토리 생성**

```bash
mkdir -p ~/Documents/second-brain/.claude/skills/{daily,weekly,monthly,inbox-processor,vault-review,braindump}
```

- [ ] **Step 2: daily/SKILL.md 작성**

```markdown
---
name: daily
description: 아침 계획 + 저녁 회고 일일 워크플로우
---

# Daily Workflow

오늘의 일일 노트를 생성하거나 업데이트합니다.

## Morning Mode (default)

1. `Daily/` 폴더에서 어제의 일일 노트를 읽고 미완료 태스크를 확인
2. `tasks.md`에서 활성 태스크 확인
3. 이번 주의 주간 리뷰(`Weekly/`)에서 주간 목표 확인
4. 오늘의 Top 3 Goals 추천
5. `Templates/daily.md` 기반으로 `Daily/YYYY-MM-DD.md` 생성
6. Top 3 Goals, 이월 태스크, 참고 컨텍스트 채우기

## Evening Mode (argument: "evening" or "저녁")

1. 오늘의 일일 노트 읽기
2. Log 섹션에서 성과, 블로커, 아이디어 추출
3. 미완료 태스크 처리:
   - 이월 → 내일로 옮김
   - 드랍 → 명시적 표시
4. Reflection 섹션 작성 유도
5. 노트 업데이트

## Rules
- 날짜 형식: YYYY-MM-DD
- `week` 속성에 해당 주간 리뷰 링크 자동 추가
- `energy` 필드는 사용자에게 질문하여 채움
- 기존 일일 노트가 있으면 덮어쓰지 않고 업데이트
```

- [ ] **Step 3: weekly/SKILL.md 작성**

```markdown
---
name: weekly
description: 주간 프로젝트 롤업 및 리뷰
---

# Weekly Review

주간 리뷰 노트를 생성합니다.

## Process

1. `Daily/` 폴더에서 이번 주 일일 노트 전체 읽기
2. 성과, 블로커, 아이디어를 종합
3. `01_Projects/` 활성 프로젝트별 진행 상황 롤업
4. `Goals/monthly-YYYY-MM.md`에서 월간 목표 대비 진척도 확인
5. 다음 주 포커스 영역 3개 설정
6. `Weekly/weekly-YYYY-WXX.md` 생성

## Output Format

```yaml
---
type: weekly
week: YYYY-WXX
month: "[[monthly-YYYY-MM]]"
---
```

### Sections
- ## This Week's Wins
- ## Blockers & Lessons
- ## Project Progress (프로젝트별 1줄 요약)
- ## Next Week Focus (Top 3)

## Rules
- 일요일 또는 주초에 실행
- 이전 주간 리뷰가 있으면 비교 제공
- 월간 목표에 자동 `[[link]]`
```

- [ ] **Step 4: monthly/SKILL.md 작성**

```markdown
---
name: monthly
description: 월간 리뷰 및 분기 마일스톤 체크
---

# Monthly Review

월간 리뷰를 수행합니다.

## Process

1. `Weekly/` 폴더에서 이번 달 주간 리뷰 전체 읽기
2. 주간 성과를 월간 단위로 종합
3. `Goals/monthly-YYYY-MM.md` 목표 대비 달성도 평가
4. `Goals/quarterly-YYYY-QX.md` 분기 마일스톤 진척도 확인
5. 활성 프로젝트가 목표에 연결되어 있는지 감사
6. 다음 달 목표 초안 제안
7. `Goals/monthly-YYYY-MM.md` 업데이트

## Audit
- 목표 없는 활성 프로젝트 경고
- 프로젝트 없는 목표 경고
- 30일 이상 업데이트 없는 프로젝트 경고

## Rules
- 월말 또는 월초에 실행
- `Goals/quarterly-YYYY-QX.md`에 자동 `[[link]]`
```

- [ ] **Step 5: inbox-processor/SKILL.md 작성**

```markdown
---
name: inbox-processor
description: Inbox 노트를 분류하고 정리
---

# Inbox Processor

`00_Inbox/` 폴더의 미처리 노트를 정리합니다.

## Process

각 노트에 대해:

1. 내용을 읽고 핵심 주제/엔티티 파악
2. 엔티티 추출 (사람, 프로젝트, 개념, 장소)
3. 볼트에서 기존 관련 노트 검색
4. `[[wikilinks]]` 추가
5. 올바른 폴더로 분류:
   - 실행 가능한 태스크 → `tasks.md`에 추가
   - 프로젝트 관련 → `01_Projects/` 해당 프로젝트로
   - 참조 자료 → `03_Resources/` (Books/, Articles/, People/)
   - 관심 영역 → `02_Areas/`
   - 아이디어/메모 → 적절한 위치 또는 유지
6. 이동 완료된 노트는 `00_Inbox/`에서 제거
7. `00_Inbox/index.md` 업데이트

## Rules
- `type` frontmatter를 반드시 추가
- 원본 내용은 보존하고, 메타데이터와 링크만 추가
- 분류가 애매한 경우 사용자에게 질문
- 처리 후 요약 보고 (N개 처리, N개 이동, N개 태스크 생성)
```

- [ ] **Step 6: vault-review/SKILL.md 작성**

```markdown
---
name: vault-review
description: 볼트 건강 상태 점검 및 정리
---

# Vault Review

볼트의 전반적 건강 상태를 검사합니다.

## Checks

1. **고아 노트**: 아무 곳에서도 링크되지 않은 노트 탐지
2. **깨진 링크**: 존재하지 않는 노트를 가리키는 `[[wikilink]]` 발견
3. **중복 콘텐츠**: 제목이나 내용이 유사한 노트 식별
4. **frontmatter 불일치**:
   - `type` 필드 누락 (필수 필드)
   - 해당 type에 필요한 필드 누락
   - `status` 값이 유효하지 않은 경우
5. **index.md 동기화**: 각 폴더의 index.md가 실제 내용과 일치하는지
6. **Stale inbox**: `00_Inbox/`에 7일 이상 된 미처리 노트
7. **목표 연결 감사**: 목표 없는 활성 프로젝트, 프로젝트 없는 목표

## Output

검사 결과를 카테고리별로 보고:
- 🔴 Critical: type 누락, 깨진 링크
- 🟡 Warning: 고아 노트, stale inbox, 미연결 목표
- 🟢 Info: 중복 후보, index 업데이트 필요

## Rules
- 파일을 수정하지 않고 보고만 함
- 수정이 필요한 경우 사용자에게 제안하고 승인 후 실행
```

- [ ] **Step 7: braindump/SKILL.md 작성**

```markdown
---
name: braindump
description: 빠른 브레인덤프를 Inbox에 캡처
---

# Braindump

$ARGUMENTS 내용을 빠르게 캡처하여 Inbox에 저장합니다.

## Process

1. `$ARGUMENTS` 내용을 파싱
2. 자동 태깅: 내용에서 키워드 추출하여 태그 생성
3. 볼트에서 관련 노트 검색
4. `00_Inbox/YYYY-MM-DD-{slug}.md` 파일 생성:

```yaml
---
type: braindump
date: YYYY-MM-DD
tags: [auto-generated]
---
```

5. 관련 노트가 있으면 `## Related` 섹션에 링크 추가
6. `00_Inbox/index.md` 업데이트

## Rules
- 최대한 빠르게 캡처 (마찰 최소화)
- 내용을 편집하지 않음 (원본 보존)
- `/inbox` 스킬로 나중에 정리
```

- [ ] **Step 8: 커밋**

```bash
cd ~/Documents/second-brain
git add .claude/skills/
git commit -m "feat: add 6 custom skills (daily, weekly, monthly, inbox, vault-review, braindump)"
```

---

### Task 8: settings.json (Hooks)

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: settings.json 작성**

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

- [ ] **Step 2: 커밋**

```bash
cd ~/Documents/second-brain
git add .claude/settings.json
git commit -m "feat: add hooks (auto-commit on write, session start reminder)"
```

---

### Task 9: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md 작성**

```markdown
# Second Brain

이것은 개인 지식 관리 + 프로젝트 관리 볼트입니다.
Claude Code가 이 파일들을 운영합니다.

## Structure
- 00_Inbox/ -- 미처리 원시 캡처, 브레인덤프
- 01_Projects/ -- 명확한 결과물이 있는 활성 작업
- 02_Areas/ -- 지속적 책임 영역 (Career, Health, Finance)
- 03_Resources/ -- 참조 자료 (Books/, Articles/, People/)
- 04_Archive/ -- 완료 또는 비활성
- 05_Attachments/ -- 이미지, PDF 등 미디어
- Daily/ -- 일일 노트 (YYYY-MM-DD.md)
- Weekly/ -- 주간 리뷰 (weekly-YYYY-WXX.md)
- Goals/ -- 목표 캐스케이드 (vision, yearly, quarterly, monthly)
- tasks.md -- 중앙 태스크 목록

## Conventions
- 모든 노트에 `type` frontmatter 필수 (daily, weekly, project, book, article, person 등)
- [[wikilinks]]를 볼트 내 노트에 사용, [text](url)은 외부 URL에만
- 태그는 #category/subcategory 형식
- 날짜는 YYYY-MM-DD 표준
- 모든 주요 폴더에 index.md 유지 (볼트 탐색 지도)

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

- [ ] **Step 2: 커밋**

```bash
cd ~/Documents/second-brain
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md vault instructions"
```

---

### Task 10: kepano 공식 스킬 설치

**Files:**
- Install: kepano/obsidian-skills (5개 스킬)

- [ ] **Step 1: obsidian-skills 저장소 클론 (임시)**

```bash
cd /tmp && git clone --depth 1 https://github.com/kepano/obsidian-skills.git
```

- [ ] **Step 2: 저장소 구조 확인**

```bash
ls /tmp/obsidian-skills/skills/ 2>/dev/null || ls /tmp/obsidian-skills/
```

Expected: `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas`, `defuddle` 폴더 확인. 경로가 다르면 실제 구조에 맞게 Step 3 조정.

- [ ] **Step 3: skills 폴더를 vault에 복사**

```bash
cp -r /tmp/obsidian-skills/skills/obsidian-markdown ~/Documents/second-brain/.claude/skills/
cp -r /tmp/obsidian-skills/skills/obsidian-bases ~/Documents/second-brain/.claude/skills/
cp -r /tmp/obsidian-skills/skills/obsidian-cli ~/Documents/second-brain/.claude/skills/
cp -r /tmp/obsidian-skills/skills/json-canvas ~/Documents/second-brain/.claude/skills/
cp -r /tmp/obsidian-skills/skills/defuddle ~/Documents/second-brain/.claude/skills/
```

- [ ] **Step 4: 임시 파일 정리**

```bash
rm -rf /tmp/obsidian-skills
```

- [ ] **Step 5: 커밋**

```bash
cd ~/Documents/second-brain
git add .claude/skills/
git commit -m "feat: install kepano/obsidian-skills (markdown, bases, cli, canvas, defuddle)"
```

---

### Task 11: Obsidian에서 vault 열기 + 검증

- [ ] **Step 1: Obsidian에서 vault 열기**

```bash
open "obsidian://open?path=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("/Users/chsong/Documents/second-brain"))')"
```

- [ ] **Step 2: 폴더 구조 검증**

```bash
cd ~/Documents/second-brain && find . -not -path './.git/*' -not -path './.obsidian/*' | sort
```

Expected: 모든 파일/폴더가 spec과 일치

- [ ] **Step 3: git log 검증**

```bash
cd ~/Documents/second-brain && git log --oneline
```

Expected: Task 1-10까지의 커밋 10개

- [ ] **Step 4: vault에서 Base 대시보드 확인**

Obsidian에서 `Bases/projects.base` 열어서 테이블 뷰가 렌더링되는지 확인.
