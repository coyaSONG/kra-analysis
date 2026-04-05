# Obsidian + Claude Code "Second Brain" 시스템 심층 리서치 보고서

**조사일:** 2026-03-19
**조사 범위:** GitHub, Reddit, YouTube, Substack, Medium, Obsidian Forum, 개인 블로그, 공식 문서
**신뢰도:** 높음 (다수의 실사용자 사례, 오픈소스 프로젝트, 공식 리소스 교차 검증)

---

## 목차

1. [핵심 요약](#1-핵심-요약)
2. [구체적 워크플로우 및 설정](#2-구체적-워크플로우-및-설정)
3. [자동화 패턴](#3-자동화-패턴)
4. [주요 프로젝트 및 템플릿](#4-주요-프로젝트-및-템플릿)
5. [실제 사용자 사례](#5-실제-사용자-사례)
6. [기술적 구현 세부사항](#6-기술적-구현-세부사항)
7. [종합 분석 및 권장사항](#7-종합-분석-및-권장사항)
8. [출처 목록](#8-출처-목록)

---

## 1. 핵심 요약

Obsidian + Claude Code 조합은 2025년 말~2026년 초에 "Second Brain" 구축의 사실상 표준 스택으로 자리잡았다. 핵심 전제는 다음과 같다:

- **Obsidian vault = 마크다운 파일 기반 코드베이스**. Claude Code가 코드베이스를 탐색하고 편집하는 능력이 그대로 노트 관리에 적용됨
- **CLAUDE.md = AI 에이전트의 행동 계약서**. 볼트 구조, 규칙, 제약조건을 정의
- **Slash commands/Skills = 반복 워크플로우 자동화**. `/daily`, `/weekly`, `/inbox` 등
- **Obsidian CLI (v1.12+) = 고성능 볼트 접근**. grep 대비 54배 빠른 검색, 토큰 70,000배 절약

3개월 이상 유지되는 시스템의 공통 특성:
- 정기적으로 사용하는 커맨드 5개 미만
- 사람이 진실성을 큐레이션하고, Claude가 정리를 담당
- Git 기반 동기화 (실시간 동기가 아닌 커밋 기반)
- 마크다운 파일이 기본 레이어

---

## 2. 구체적 워크플로우 및 설정

### 2.1 볼트 구조 패턴

실사용자들이 채택하는 주요 폴더 구조는 크게 3가지 패턴으로 분류된다.

#### 패턴 A: PARA 기반 (가장 보편적)

Claudesidian, ballred/obsidian-claude-pkm 등 대부분의 스타터킷이 채택.

```
vault/
├── CLAUDE.md                  # AI 행동 규칙
├── .claude/
│   ├── commands/              # 슬래시 커맨드 (deprecated, skills로 통합 중)
│   ├── skills/                # Agent Skills
│   ├── hooks/                 # 자동화 훅
│   └── settings.json          # 권한, 환경변수
├── 00_Inbox/                  # 빠른 캡처
├── 01_Projects/               # 시간 한정 작업
├── 02_Areas/                  # 지속적 책임 영역
├── 03_Resources/              # 참조 자료
├── 04_Archive/                # 완료/비활성 항목
├── 05_Attachments/            # 이미지, PDF 등
├── Daily Notes/               # YYYY-MM-DD.md
├── Goals/                     # 목표 캐스케이드
├── Templates/                 # 재사용 템플릿
└── tasks.md                   # 중앙 태스크 목록
```

#### 패턴 B: 번호 접두사 + PARA + Zettelkasten 하이브리드

Stefan Imhoff, Kenneth Reitz 등이 채택. 6,000+ 노트 규모의 대형 볼트에 적합.

```
vault/
├── 00 - Maps of Content/      # MOC (주제별 허브 노트)
├── 01 - Projects/             # 활성 프로젝트
│   ├── Project 1/
│   └── Project 2/
├── 02 - Areas/                # 관심 영역
│   ├── Finance & Investment/
│   ├── Fitness & Health/
│   └── ...
├── 03 - Resources/            # 참조 자료
│   ├── Books/
│   ├── Movies/
│   ├── People/
│   ├── Podcasts/
│   ├── Companies/
│   └── Quotes/
├── 04 - Permanent/            # 잘 정리된 영구 노트 (Zettelkasten)
├── 05 - Fleeting/             # 임시 노트 (Zettelkasten)
├── 06 - Daily/                # 일일 노트
│   └── 2026/
├── 07 - Archives/             # 보관함
├── 99 - Meta/                 # 메타 정보
│   ├── assets/
│   ├── bases/
│   ├── graphs/
│   ├── scripts/
│   └── templates/
└── CLAUDE.md
```

#### 패턴 C: 플랫 구조 + 연결 우선 (Steph Ango / kepano 스타일)

Obsidian CEO가 직접 사용하는 방식. 최대한 단순하게.

```
vault/
├── [대부분의 노트는 루트에 위치]
├── References/                # 외부 주제 (책, 영화, 인물)
├── Clippings/                 # 웹 클리핑
├── Attachments/               # 미디어 파일
├── Daily/                     # YYYY-MM-DD.md
├── Templates/                 # 템플릿
└── Categories/                # 카테고리별 MOC
```

**kepano의 핵심 규칙:**
1. 단일 볼트 유지 (분리하지 않음)
2. 폴더 사용 최소화
3. 표준 마크다운만 사용
4. 카테고리와 태그는 복수형으로
5. 내부 링크를 광범위하게 사용
6. 날짜는 `YYYY-MM-DD` 표준화
7. 7점 척도 평가 시스템

### 2.2 CLAUDE.md 작성 패턴

#### 기본 템플릿 (Michael Crist 제안)

```markdown
# CLAUDE.md

## Who I Am
[이름, 역할, 하는 일]

## What I'm Working On
[현재 프로젝트, 우선순위, 마감일]

## How This Vault Is Organized
[폴더 구조 간단 설명, 핵심 파일 위치]

## How I Want You to Work
- 해당 폴더의 index.md를 먼저 읽고 작업할 것
- 파일 삭제/덮어쓰기 전 확인할 것
- 응답은 간결하게

## Maintenance
- 파일 생성/삭제 시 해당 폴더의 index.md 업데이트
```

#### 고급 CLAUDE.md (Kenneth Reitz 스타일)

```markdown
# Vault Context

이 볼트는 [목적] 작업 지식 베이스입니다.
노트는 Obsidian Flavored Markdown으로 작성됩니다.

## Structure
- Projects/ -- 마감이 있는 활성 작업
- Areas/ -- 지속적 관심 영역
- Resources/ -- 참조/에버그린 콘텐츠
- Archive/ -- 완료된 작업

## Conventions
- 태그는 #category/subcategory 형식 사용
- MOC 노트는 "MOC -- " 접두사로 명명
- 소스 노트는 frontmatter에 `source:` 필드 포함
- [[wikilinks]]를 볼트 내 노트에 사용 (Obsidian이 이름 변경 자동 추적)
- [text](url)은 외부 URL에만 사용

## What NOT To Do
- 명시적 요청 없이 파일 생성하지 않음
- 폴더 계층 재구조화하지 않음
- 이모지 추가하지 않음
- 단순한 요청을 과도하게 엔지니어링하지 않음
- 정신 건강 관련 콘텐츠에 대해 편집하지 않음

## Active Context
- 현재 작업 중: [세션 전 업데이트]
- 미해결 질문: [막힌 부분]
```

#### 운영 중심 CLAUDE.md (okhlopkov 스타일)

```markdown
# Second Brain

이것은 나의 개인 지식 볼트입니다. Claude Code가 이 파일들을 운영합니다.

## Structure
- inbox/ -- 미처리 원시 캡처, 브레인덤프
- projects/ -- 명확한 결과물이 있는 활성 작업
- areas/ -- 지속적 책임
- resources/ -- 참조 자료
- archive/ -- 완료 또는 비활성

## Processing Rules
- 파일 하나에 아이디어 하나. 설명적 파일명.
- 모든 사람, 프로젝트, 개념에 [[wiki-links]] 사용
- 모든 폴더에 contents를 나열하는 index.md 보유
- 일일 노트는 날짜 접두사: YYYY-MM-DD.md
- 인박스 처리 시: 엔티티 추출, 링크 추가, 올바른 폴더로 분류

## Voice Message Rules
- 원본 전사는 절대 수정하지 않음
- personal/diary/YYYY-MM-DD [요약].md로 저장
- 원본 텍스트 아래에 태그와 프로젝트 링크 추가
- 실행 가능한 항목을 tasks.md 또는 프로젝트별 태스크 파일로 추출
```

### 2.3 Frontmatter / Properties 스키마

사용자들이 표준화하는 공통 스키마:

#### 일일 노트
```yaml
---
type: daily
date: 2026-03-19
week: "[[2026-W12]]"
---
```

#### 엔티티 노트 (사람, 팀, 프로젝트 등)
```yaml
---
type: person
name: "홍길동"
role: "Engineering Manager"
team: "Platform"
status: active
tags: [people, engineering]
---
```

#### 리소스 노트 (책, 영화 등)
```yaml
---
type: book
title: "책 제목"
author: "저자명"
rating: 6
genre: [비즈니스, 심리학]
date_read: 2026-03-15
cover: "assets/covers/book-cover.webp"
---
```

#### Kenneth Reitz의 범용 스키마
```yaml
---
type: note          # note, template, log, index
role: documentation # documentation, reflection, analysis
status: active      # active, archived
date: 2026-03-19
themes:             # 교차 참조 및 패턴 발견용
  - productivity
  - ai-workflow
---
```

#### Steph Ango의 Properties 원칙
- 카테고리 간 재사용 가능한 이름 (예: `genre`를 영화, 책, 음악에 공통 사용)
- 짧은 이름 선호 (`start` vs `start-date`)
- 다중 값에는 기본적으로 list 타입 사용

### 2.4 슬래시 커맨드 / 커스텀 Skills

#### 커맨드 파일 위치와 구조

```
.claude/
├── commands/              # 팀 공유 (git 추적)
│   ├── daily.md
│   ├── weekly.md
│   └── review.md
│
# 또는 최신 통합 패턴 (Claude Code 2.1+):
├── skills/
│   ├── daily/SKILL.md
│   ├── weekly/SKILL.md
│   └── inbox-processor/SKILL.md

~/.claude/
└── commands/              # 개인용 (git 미추적)
    └── my-debug.md
```

#### 핵심 커맨드 예시

**/daily** (아침 계획 + 저녁 회고):
```markdown
# Daily Workflow

오늘의 일일 노트를 생성하거나 업데이트합니다.

## Morning
1. 어제의 일일 노트를 읽고 미완료 태스크를 확인
2. 주간 리뷰에서 이번 주 Top 3 목표 확인
3. 오늘의 OKR 정렬 포커스 설정
4. 캘린더 확인 후 시간 블록 구성

## Evening
1. 오늘의 로그를 스캔하여 성과, 블로커, 아이디어 추출
2. 미완료 태스크 처리 (이월 또는 명시적 드랍)
3. 감사/회고 섹션 작성
4. 내일을 위한 AI 컨텍스트 설정
```

**/my-world** (Internet Vin / Greg Isenberg 워크플로우):
```markdown
# Load Full Vault Context

볼트의 모든 핵심 파일을 읽어 전체 컨텍스트를 로드합니다.
프로젝트, 우선순위, 사람 관계, 지식 그래프를 한 번에 파악합니다.

1. CLAUDE.md 읽기
2. 모든 프로젝트 폴더의 overview.md 읽기
3. 현재 주간/월간 리뷰 읽기
4. 최근 3일간 일일 노트 읽기
5. 활성 태스크 목록 읽기
```

**/ghost** (본인 목소리로 답변):
```markdown
# Ghost Writer

볼트의 기존 글들을 분석하여 나의 어조, 스타일, 관점으로 답변합니다.
$ARGUMENTS 에 대해 내가 직접 쓴 것처럼 작성합니다.

1. Resources/ 폴더에서 관련 기존 글 검색
2. 어조와 스타일 패턴 분석
3. 해당 주제에 대한 내 입장과 관점 파악
4. 일관된 목소리로 초안 작성
```

**/trace** (아이디어 진화 추적):
```markdown
# Trace Idea Evolution

$ARGUMENTS 개념이 볼트에서 어떻게 진화해왔는지 추적합니다.

1. 해당 개념의 첫 언급 시점 찾기
2. 시간순으로 관련 노트 나열
3. 개념의 변화/발전 과정 분석
4. 현재 상태와 미래 방향 제시
```

**/vault-review** (볼트 건강 점검):
```markdown
# Vault Health Check

볼트의 전반적 상태를 검사합니다.

1. 고아 노트 (아무 곳에서도 링크되지 않은 노트) 탐지
2. 깨진 링크 확인
3. 중복 콘텐츠 식별
4. frontmatter 일관성 검사
5. index.md 파일 최신 상태 확인
6. 최근 7일간 수정되지 않은 inbox 항목 경고
```

**/log** (마찰 없는 일일 로깅):
```markdown
# Quick Log Entry

$ARGUMENTS 내용을 오늘의 일일 노트 로그 섹션에 추가합니다.
이모지 마커 자동 분류: 💡(아이디어), 🎉(성과), ⚠️(블로커)
```

---

## 3. 자동화 패턴

### 3.1 자동 링킹 워크플로우

**Kyle Gao의 실제 사용 방식** (가장 상세하게 문서화된 사례):

```
사용자: "오늘 저널 항목을 읽고 언급된 모든 사람, 장소, 책에 대한
        백링크를 추가해줘"

Claude Code 실행 과정:
1. 일일 노트 읽기
2. 볼트에서 기존 엔티티 노트 검색
3. 새로운 엔티티의 경우 노트 생성
4. 문서 전체에 적절한 [[wiki-links]] 추가
```

**Stefan Imhoff의 대규모 백링킹** (6,000+ 노트):

Claude Code에게 다음을 요청:
1. 일일 노트 전체를 검토하여 새 리소스 유형 식별
2. 각 유형별 템플릿 생성 (podcast, company 등)
3. 스크립트를 만들어 책 커버, 인물 사진, 영화 포스터 자동 다운로드
4. YAML frontmatter 메타데이터 자동 채우기
5. 모든 일일 노트를 순회하며 백링크 생성

### 3.2 일일 노트 자동화

#### Nori Nishigaya의 "Good Morning" 스킬 (6단계 프로세스)

```
Phase 1 - Context Reload:
  어제의 일일 노트 읽기 → 성과, 블로커, 결정, 이월 항목 추출

Phase 2 - OKR Alignment:
  분기 OKR + 주간/월간 목표 검토 → 오늘의 우선순위 영역 식별

Phase 3 - Task Prioritization:
  TaskNotes 폴더의 모든 open/in-progress 태스크 스캔 →
  OKR 정렬도, 우선순위, 일정 적합성, 에너지 요구, 블로킹 상태로 점수화 →
  Top 3 추천

Phase 4 - Confirmation:
  Top 3 추천 제시 → 사용자 조정 수락 → 일일 노트 업데이트

Phase 5 - Calendar Integration:
  스프린트 주차 결정 → 정기 회의 확인 → 추가 시간 블록 프롬프트

Phase 6 - Daily Note Population:
  오늘 노트 생성 → OKR Quick Check 채우기 → Top 3 Goals 확정
```

#### Chase Adams의 자동화 스크립트 (Bun/TypeScript)

```typescript
// 000 OS/Claude/scripts/setup-week.ts
// 다음 주의 Weekly + Daily 노트를 자동 생성

// 실행: bun run 000\ OS/Claude/scripts/setup-week.ts [optional-date]

function createWeeklyNote(monday: Date) {
  // ISO 주차 형식으로 100 Periodics/Weekly/ 에 생성
}

function createDailyNote(date: Date) {
  // 월~금 일일 노트를 100 Periodics/Daily/ 에 생성
}
```

### 3.3 인박스 처리 (Capture → Organize → Distill)

#### GTD 스타일 인박스 처리 패턴

```markdown
# Inbox Processor Skill

세션 시작 시 inbox/ 폴더에 미처리 노트가 있는지 확인합니다.
존재하면 처리를 제안합니다:

## Processing Steps
1. 각 노트에서 엔티티 추출 (사람, 프로젝트, 개념)
2. [[wiki-links]] 추가
3. 올바른 폴더로 분류:
   - 실행 가능 → Projects/ 또는 tasks.md
   - 참조 자료 → Resources/
   - 아이디어 → Fleeting/ 또는 Areas/
   - 완료/비활성 → Archive/
4. index.md 업데이트
```

#### Claudesidian의 접근 방식

```
/inbox-processor 커맨드:
- "Thinking Mode" 우선: AI가 질문을 통해 아이디어를 탐색하고,
  기존 노트를 검색하여 인사이트를 기록
- "Writing Mode" 후행: 리서치를 바탕으로 콘텐츠 생성,
  구조화, 편집, 최종 산출물 제작
```

### 3.4 Claude Code Hooks를 이용한 자동화

Hooks는 Claude Code의 수명주기에서 자동 실행되는 셸 스크립트다. CLAUDE.md가 "제안"인 반면, Hooks는 "보장된 실행"을 제공한다.

```json
// ~/.claude/settings.json 또는 .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "cd $(git rev-parse --show-toplevel) && git add -A && git commit -m \"checkpoint: $(date +%H:%M)\"",
        "description": "모든 파일 변경 후 자동 커밋"
      }
    ],
    "SessionStart": [
      {
        "command": "echo '오늘의 포커스와 미완료 태스크를 확인하세요'",
        "description": "세션 시작 시 리마인더"
      }
    ],
    "Stop": [
      {
        "command": "cd $(git rev-parse --show-toplevel) && git add -A && git commit -m \"session end: $(date +%Y-%m-%d)\"",
        "description": "세션 종료 시 최종 커밋"
      }
    ]
  }
}
```

**6가지 Hook 이벤트:**
1. `SessionStart` -- 세션 초기화 시
2. `UserPromptSubmit` -- 사용자 프롬프트 제출 직후
3. `PreToolUse` -- 도구 실행 직전
4. `PostToolUse` -- 도구 실행 직후
5. `PreCompact` -- 대화 압축 직전
6. `Stop` -- 세션 종료 시

### 3.5 볼트 유지보수 자동화

**Eleanor Konik의 실제 사용 (15M 단어 볼트):**

> "Claude Code가 내 전체 볼트(1,500만 단어)를 밤새 순회하면서 깔끔한 인덱스 파일을 만들었다. 임신 이후 연결하지 못했던 것들을 찾아냈고, 손대지 못했던 파일들을 정리하고, RSS 플러그인의 문자 인코딩 글리치를 수정하고, 오래된 메타데이터를 새 기준에 맞게 업데이트했다. 모두 풀 리퀘스트 형태로, 데이터 파괴 위험 없이."

**핵심 팁:**
- Claude가 수정 사항을 발견할 때마다 관련 skill 파일이나 CLAUDE.md에 그 실수를 방지하는 지침을 기록하도록 설정
- `.claude` 폴더나 inbox에 대화 로그, 문제점, 수정사항을 기록하는 파일 설정

---

## 4. 주요 프로젝트 및 템플릿

### 4.1 kepano/obsidian-skills (공식 Obsidian Skills)

**GitHub:** https://github.com/kepano/obsidian-skills
**Stars:** 14.6k+ | **License:** MIT | **관리자:** Steph Ango (Obsidian CEO)

Obsidian과 함께 사용하기 위한 공식 Agent Skills 세트.

#### 포함된 스킬 5종

| 스킬 | 파일 | 기능 |
|------|------|------|
| **obsidian-markdown** | `skills/obsidian-markdown/SKILL.md` | Obsidian Flavored Markdown 생성/편집. Wikilinks, 임베드, 콜아웃, Properties, 수학 수식, Mermaid 다이어그램 규칙 |
| **obsidian-bases** | `skills/obsidian-bases/SKILL.md` | `.base` 파일 생성. 데이터베이스 뷰, 필터, 수식, 요약 기능의 대시보드 구축 |
| **json-canvas** | `skills/json-canvas/SKILL.md` | `.canvas` 파일 생성. 텍스트/파일/링크/그룹 노드와 엣지 연결로 시각적 캔버스 |
| **obsidian-cli** | `skills/obsidian-cli/SKILL.md` | Obsidian CLI로 볼트와 상호작용. 노트 CRUD, 검색, 백링크, 태그, 일일 노트, 속성 관리, 플러그인 개발 |
| **defuddle** | `skills/defuddle/SKILL.md` | 웹 콘텐츠에서 깨끗한 마크다운 추출. 불필요한 요소 제거로 토큰 절약 |

#### 설치 방법

```bash
# Marketplace 설치
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills

# NPX 설치
npx skills add git@github.com:kepano/obsidian-skills.git

# 수동 설치 (Claude Code)
# repo 내용을 볼트 루트의 /.claude 폴더에 복사
```

#### obsidian-cli 핵심 커맨드

```bash
# 노트 읽기/생성/추가
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"

# 검색 및 분석
obsidian search query="search term" limit=10
obsidian backlinks file="My Note"
obsidian tags sort=count counts

# 일일 노트 조작
obsidian daily:read
obsidian daily:append content="- [ ] New task"

# 속성 관리
obsidian property:set name="status" value="done" file="My Note"

# 개발자 도구
obsidian eval code="app.vault.getFiles().length"
obsidian dev:screenshot path=screenshot.png
obsidian plugin:reload id=my-plugin
```

**성능 비교 (grep vs Obsidian CLI):**
- 고아 노트 탐지: grep 15.6초 vs CLI 0.26초 (**54배 빠름**)
- 볼트 검색: grep 1.95초 vs CLI 0.32초 (**6배 빠름**)
- 토큰 비용: grep 대비 약 **70,000배 저렴**

#### obsidian-bases로 대시보드 만들기

`.base` 파일은 YAML 형식이며, Obsidian 노트를 데이터베이스 뷰로 표시:

```yaml
# projects.base
filters:
  - file.inFolder("01 - Projects")
  - status != "archived"

formulas:
  days_active: "(now() - file.ctime).days"
  is_stale: 'if(days_active > 30, "Yes", "No")'

properties:
  file.name:
    displayName: "Project"
  status:
    displayName: "Status"
  formula.days_active:
    displayName: "Days Active"

views:
  - type: table
    name: "Active Projects"
    order:
      - file.name
      - status
      - formula.days_active
    summaries:
      formula.days_active: "values.mean().round(0)"
```

마크다운에 임베드: `![[projects.base]]`

### 4.2 Claudesidian (heyitsnoah/claudesidian)

**GitHub:** https://github.com/heyitsnoah/claudesidian
**Stars:** 1,300+ | **License:** MIT

Claude Code + Obsidian 통합을 위한 완전한 스타터킷.

#### 핵심 특징

- **PARA 폴더 구조** 내장
- **대화형 설정 마법사** (`/init-bootstrap`): 기존 볼트 분석, 안전한 마이그레이션, 개인화된 CLAUDE.md 생성
- **6개 사전 구성 커맨드:**
  - `/thinking-partner` -- AI 사고 파트너
  - `/inbox-processor` -- 인박스 자동 정리
  - `/research-assistant` -- 심층 리서치
  - `/daily-review` -- 일일 검토
  - `/weekly-synthesis` -- 주간 종합
  - `/de-ai-ify` -- AI 문체 제거
- **선택적 고급 통합:**
  - Gemini Vision MCP: 이미지/PDF 직접 분석
  - Firecrawl: 웹 콘텐츠 스크래핑 후 볼트에 저장

#### 설치 및 설정

```bash
git clone https://github.com/heyitsnoah/claudesidian.git my-vault
cd my-vault
claude
/init-bootstrap
```

#### 내장 자동화 스크립트

```bash
npm run attachments:list      # 미처리 첨부파일 나열
npm run attachments:orphans   # 참조되지 않는 파일 찾기
npm run vault:stats           # 볼트 통계 표시
npm run firecrawl:scrape      # 웹 페이지 스크래핑
```

### 4.3 ballred/obsidian-claude-pkm

**GitHub:** https://github.com/ballred/obsidian-claude-pkm
**Stars:** 1,181+ | **License:** MIT | **Version:** 3.1

"단순한 PKM 스타터킷이 아닌, 실행 시스템"을 표방.

#### 핵심 차별점: 목표 캐스케이드 아키텍처

```
3-Year Vision ──→ Yearly Goals ──→ Projects ──→ Monthly Goals ──→ Weekly Review ──→ Daily Tasks
                                      ↑
                              /project new
                         (the bridge layer)
```

모든 레이어가 연결됨:
- `/daily`이 주간 리뷰에서 ONE Big Thing을 표면화
- `/weekly`가 프로젝트 진행 상황을 표시
- `/monthly`가 분기 마일스톤 체크
- `/goal-tracking`이 활성 프로젝트가 없는 목표를 플래그

#### Skills 목록 (10개)

| 스킬 | 기능 |
|------|------|
| `/daily` | 아침 계획, 오후 체크인, 저녁 회고 |
| `/weekly` | 30분 리뷰, 프로젝트 롤업 |
| `/monthly` | 월간 리뷰, 분기 마일스톤 검증 |
| `/project` | 프로젝트 생성, 추적, 보관 (목표 연결) |
| `/review` | 스마트 라우터 (아침/일요일/월말 자동 감지) |
| `/push` | Git 커밋 및 푸시 |
| `/onboard` | 대화형 설정, 볼트 컨텍스트 로딩 |
| `/adopt` | 기존 볼트에 스캐폴딩 (PARA, Zettelkasten, LYT 자동 감지) |
| `/upgrade` | 콘텐츠 보존하며 최신 버전 업데이트 |
| `/goal-tracking` | 목표-프로젝트 연결 감사 |

#### AI Agents (4개)

1. **goal-aligner** -- 일일 활동과 명시된 목표 간 불일치 감사
2. **weekly-reviewer** -- 3단계 리뷰 촉진, 회고 스타일 학습
3. **note-organizer** -- 깨진 링크 수정, 중복 통합
4. **inbox-processor** -- GTD 스타일 인박스 처리

#### 자동화 Hooks

- **PostToolUse Auto-commit:** 모든 파일 쓰기가 Git 커밋 트리거
- **SessionStart:** ONE Big Thing, 활성 프로젝트 수, 마지막 리뷰 이후 일수 표시

### 4.4 hancengiz/cc-obsidian-vault-api-skill

**GitHub:** https://github.com/hancengiz/cc-obsidian-vault-api-skill

Obsidian의 Local REST API 플러그인을 통해 볼트와 상호작용하는 Claude Code Skill.

- 31개 API 엔드포인트 (OpenAPI 스펙 포함)
- Dataview 쿼리 실행 지원
- 17개 파괴적 작업에 대한 안전장치
- Claude Code, Claude Desktop, claude.ai 모두 지원

```bash
# 원라인 설치
curl -fsSL https://raw.githubusercontent.com/hancengiz/obsidian-vault-skill/main/scripts/remote-install.sh | bash -s -- --user
```

### 4.5 기타 주목할 프로젝트

| 프로젝트 | 설명 |
|----------|------|
| **Claudian** (YishenTu/claudian) | Obsidian 플러그인으로 Claude Code를 볼트 내부에 임베드 |
| **obsidian-claude-code-mcp** (iansinnott) | WebSocket 기반 MCP 서버, Claude Code가 자동으로 볼트 발견 (포트 22360) |
| **mcp-obsidian** (smithery-ai) | Claude Desktop용 Obsidian MCP 커넥터 (Stars: 1.3k) |
| **QMD** (tobi) | Shopify CEO가 만든 로컬 마크다운 검색 엔진 (BM25 + 벡터 + LLM 리랭킹) |
| **ashish141199/obsidian-claude-code** | 미니멀 볼트 템플릿 (Topics + MOCs + Daily Notes 구조) |

---

## 5. 실제 사용자 사례

### 5.1 Teresa Torres (Continuous Discovery Habits 저자)

**설정:** Claude Code + Obsidian + Python cron jobs + Node.js 스크립트

- 커스텀 `/today` 슬래시 커맨드로 매일 태스크 컴파일
- 자동화된 리서치 파이프라인: arXiv/Google Scholar 쿼리 → PDF 다운로드 → Claude 요약
- **핵심 관행:** 세션 종료 시 "오늘 우리가 문서화해야 할 것을 배웠나요?" 의식
- 초기 단일 CLAUDE.md가 비효율적이라 판단 → **수십 개의 작고 집중된 참조 파일 + 인덱스 맵**으로 분리
- 결과: 단순한 프롬프트로도 "정확하고 잘 조정된 비평" 생성

### 5.2 Huy Tieu

- **초기:** 25개 커맨드로 시작
- **최적화 후:** 4개 핵심 인터랙션으로 축소
  - `/daily-brief`
  - `/braindump`
  - `/weekly-checkin`
  - `/consolidate-knowledge`
- 3개월간 120+ 브레인덤프 처리
- 월간 통합에서 "40개 이상의 산재된 브레인덤프에서 일관된 15페이지 전략 분석" 생성
- **비용:** 월 $10-15 API

### 5.3 Stefan Imhoff (디자인 + 개발)

- **규모:** 6,000+ 노트
- **구조:** PARA + Zettelkasten 하이브리드 (번호 접두사)
- **자동화 작업:**
  - 모든 이미지를 webp로 변환
  - 에셋을 하위폴더로 분류 (인물 사진, 영화 커버 등)
  - 무의미한 파일명을 이미지 내용 분석 후 설명적 이름으로 변경
  - 모든 링크 참조 자동 업데이트
  - 책 커버, 인물 사진, 영화/TV 커버 다운로드 스크립트 생성
  - YAML frontmatter 메타데이터 자동 채우기
  - 일일 노트 순회하며 백링크 생성
  - 새 리소스 유형 식별 및 생성 (podcast, company 등)
  - QMD + D3.js로 커스텀 대화형 그래프 시각화 생성
- **도구:** Obsidian CLI + QMD (Shopify CEO의 로컬 검색 엔진)

### 5.4 Nori Nishigaya (ADHD 뇌에 최적화)

- **이전:** 매일 아침 20분을 "오늘 뭐 할까" 파악에 소비
- **이후:** "Good morning" 타이핑으로 AI가 오늘 중요한 것을 정확히 알려줌
- **핵심 스킬 4개:**
  - `/log` (마찰 없는 일일 로깅, 음성 모드 지원)
  - `/task` (자동 메타데이터 강화: 우선순위, 에너지, 시간 추정, 프로젝트 연결)
  - Good Morning 스킬 (6단계 아침 루틴)
  - `/harvest` (하루 마감 의식)
- **이모지 마커 시스템:** 💡(아이디어), 💭(생각), ❤️(감사), 🎉(성과), ⚠️(블로커)
- **ADHD 최적화:** 최소 마찰, 자동 컨텍스트 생성, 축하 우선 수확 의식

### 5.5 Eleanor Konik (15M 단어 볼트)

- 볼트를 밤새 순회하여 인덱스 파일 생성
- RSS 플러그인 문자 인코딩 글리치 수정
- 오래된 메타데이터를 새 기준에 맞게 업데이트
- 모두 풀 리퀘스트로 진행 (데이터 안전)
- **팁:** "볼트를 상위 폴더에 넣고, `cd ..`으로 올라가면 코드 저장소와 볼트를 동시에 접근 가능"

### 5.6 Damian Galarza (개발자 워크플로우)

- **설정:** Linear (PM) + Sentry (에러) + Memory MCP + Obsidian
- Obsidian 노트 경로: `01-Projects/DHF Extraction/2025-11-01-Pairing Session.md`
- `/add-dir ~/second-brain`으로 Claude Code에 볼트 연결
- Linear 이슈 ID로 구현을 시작하는 통합 Agent Skill:
  1. Linear 이슈 세부사항 가져오기
  2. 관련 Obsidian 노트 참조
  3. Sentry 예외 확인
  4. GitHub 토론 연결
  5. 구현 계획 생성 → 인간 승인 → 코드 작성

### 5.7 Steffi Kieffer (비개발자 / LinkedIn 공유)

**3단계 프로세스:**
1. ChatGPT가 산책/목욕/소파에서 주제별 인터뷰 → MD 파일 생성 → Obsidian으로 이동
2. Claude Code와 설정 논의 → 폴더 구조 + CLAUDE.md 생성
3. Claude Code가 발행된 뉴스레터 읽기 → 핵심 개념 추출 → MD 파일로 지식 라이브러리 구축

**핵심 교훈:**
- "AI와 함께 구축하되, AI가 대신 구축하게 하지 마라" -- v1.0은 완전히 Claude 주도였지만 본인의 사고방식과 맞지 않았음. v2.0은 협업.

### 5.8 Internet Vin + Greg Isenberg (YouTube 인터뷰, 178K 조회)

**핵심 커맨드 세트:**

| 커맨드 | 기능 |
|--------|------|
| `/my-world` (원래 `/context`) | 전체 볼트 컨텍스트 로드 |
| `/today` | 아침 계획 |
| `/close` | 저녁 회고 |
| `/trace` | 아이디어 진화 추적 |
| `/ghost` | 본인 목소리로 답변 |
| `/connect` | 두 영역 간 연결 발견 |
| `/challenge` | 기존 사고에 도전 |
| `/emerge` | 잠재적 패턴 표면화 |
| `/drift` | 자유로운 아이디어 탐색 |
| `/ideas` | 볼트 기반 아이디어 생성 |
| `/graduate` | 아이디어를 프로젝트로 승격 |

**핵심 원칙:** "에이전트는 읽고, 인간은 쓴다." 볼트에는 진정성 있는 사고만 보존하고, Claude 출력물은 `~/.claude/`에 별도 저장.

**"The Alpha":** "글쓰기는 에이전트에게 일을 위임하는 주요 방법이다. 글쓰기 습관을 기르면, 에이전트에게 넘길 수 있는 컨텍스트가 훨씬 많아진다."

---

## 6. 기술적 구현 세부사항

### 6.1 Claude Code와 Obsidian 연결 방법 (5가지)

| 방법 | 장점 | 단점 | 적합 대상 |
|------|------|------|-----------|
| **볼트 디렉토리에서 `claude` 실행** | 가장 간단, 설정 불필요 | 한 번에 하나의 볼트만 | PKM/Second Brain 사용자 |
| **`--add-dir` 플래그** | 다른 프로젝트에서 볼트 참조 | 매 세션마다 지정 필요 | 개발자 |
| **사용자 레벨 CLAUDE.md 임포트** | 자동 로드 | 과도한 컨텍스트 소비 가능 | 볼트가 작을 때 |
| **Symlink 기반** | 다중 리포 통합 검색 | 설정 복잡 | 멀티 프로젝트 개발자 |
| **MCP Bridge** | 리포를 깨끗하게 유지 | Obsidian 실행 필요 | 엔터프라이즈 |

#### 연결 방법 상세

```bash
# 방법 1: 볼트 디렉토리에서 직접 실행
cd ~/obsidian-vault && claude

# 방법 2: 다른 프로젝트에서 볼트 참조
claude --add-dir ~/second-brain

# 방법 3: 사용자 레벨 자동 임포트
echo '@~/second-brain/CLAUDE.md' >> ~/.claude/CLAUDE.md

# 방법 4: Symlink 기반
mkdir ~/Developer-Vault
ln -s ~/.claude claude-global
ln -s ~/obsidian-vault vault
ln -s ~/projects/my-app my-app

# 방법 5: MCP Bridge (obsidian-claude-code-mcp 플러그인)
# Obsidian에서 플러그인 설치 → Claude Code가 WebSocket으로 자동 발견
```

### 6.2 Obsidian 내부에서 Claude Code 실행하기

**필요한 플러그인:**
1. **Terminal 플러그인** -- Obsidian 내에서 터미널 열기
2. **obsidian-skills** -- `.claude` 폴더에 Agent Skills 배치

**대안:**
- **Claudian 플러그인** (YishenTu/claudian) -- 사이드바 채팅 UI
- **Agent Client 플러그인** -- `@notename`으로 노트 멘션 지원
- **Claude Sidebar 플러그인** -- 임베디드 터미널

### 6.3 모바일 캡처 및 동기화

| 방법 | 비용 | 특징 |
|------|------|------|
| **Obsidian Sync** | $5/월 | E2E 암호화, 네이티브 |
| **Syncthing** | 무료 | P2P 동기화 |
| **iCloud** | 무료 | macOS/iOS 네이티브 |
| **Git (GitHub)** | 무료 | 백업 + 버전 관리 |
| **Takopi** (Telegram 브릿지) | 무료 | 음성 메시지 → Whisper 전사 → Claude 처리 |

### 6.4 MCP 서버 비용 고려사항

- 각 MCP 서버: 기본 600-800 토큰 소비
- 일반적 서버 (20-30 도구): ~20,000 토큰
- 실용적 한계: 5개 미만 관리 가능, 5-10개 빡빡함, 10개 초과 비실용적

### 6.5 벡터 검색 통합 (500+ 문서 시)

```sql
-- pgvector 기반 지식 검색
create extension if not exists vector;

create table knowledge (
  id serial primary key,
  content text not null,
  source text,
  content_hash text unique,
  metadata jsonb,
  embedding vector(1536),
  created_at timestamptz default now()
);

create index on knowledge using hnsw (embedding vector_cosine_ops);

create or replace function search_knowledge(
  query_embedding vector(1536),
  match_count int default 5
)
returns table (id int, content text, source text, similarity float)
language sql stable
as $$
  select id, content, source,
    1 - (embedding <=> query_embedding) as similarity
  from knowledge
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

### 6.6 필수 Obsidian 플러그인 스택

| 플러그인 | 용도 | 필수도 |
|----------|------|--------|
| **Dataview** | 쿼리, 동적 리스트, 메타데이터 필터링 | 필수 |
| **Periodic Notes** | 일일/주간/월간/분기 노트 자동 생성 | 필수 |
| **Templater** | 동적 템플릿 (날짜 변수, 조건부 콘텐츠) | 필수 |
| **Calendar** | 사이드바 날짜 네비게이션 | 권장 |
| **QuickAdd** | 타임스탬프와 함께 빠른 캡처 | 권장 |
| **Obsidian Git** | 버전 관리, 자동 백업 | 권장 |
| **File Explorer++** | 와일드카드/정규식 필터링 | 선택 |
| **Kanban** | 마크다운 기반 프로젝트 보드 | 선택 |
| **Smart Connections** | AI 기반 유사 노트 제안 | 선택 |
| **TaskNotes** | 텍스트 기반 태스크 (Claude 친화적) | 선택 |

### 6.7 스킬 조합 패턴

#### 패턴 1: 모듈형 스킬 구성 (Eleanor Konik 권장)

> "스킬(또는 커맨드)을 함수처럼 취급하라. 반복하지 마라. 두 커맨드가 다른 스킬을 호출하도록 하고, 그 하나의 스킬만 업데이트하면 된다."

```
.claude/skills/
├── core/
│   ├── read-context/SKILL.md      # 컨텍스트 로딩 (다른 스킬이 호출)
│   └── update-index/SKILL.md      # 인덱스 업데이트 (다른 스킬이 호출)
├── daily/SKILL.md                 # core/read-context 호출 후 일일 워크플로우
├── weekly/SKILL.md                # core/read-context 호출 후 주간 리뷰
└── vault-review/SKILL.md          # core 모두 호출 후 전체 점검
```

#### 패턴 2: 계층형 리뷰 시스템 (ballred/obsidian-claude-pkm)

```
/review 스마트 라우터:
  - 아침이면 → /daily morning 모드
  - 일요일이면 → /weekly 트리거
  - 월말이면 → /monthly 트리거

/daily → /weekly → /monthly → /goal-tracking
  ↑각 레이어가 아래 레이어의 데이터를 롤업
```

#### 패턴 3: 외부 통합 파이프라인 (Damian Galarza)

```
Linear Issue → /implement skill:
  1. Linear MCP → 이슈 세부사항
  2. Obsidian → 관련 프로젝트 노트
  3. Sentry MCP → 관련 에러
  4. GitHub → 관련 PR/토론
  5. Memory MCP → 이전 구현 계획
  → 통합 컨텍스트로 구현 계획 생성
  → 인간 승인 체크포인트
  → 코드 작성
```

---

## 7. 종합 분석 및 권장사항

### 7.1 성공하는 시스템의 공통 패턴

1. **단순하게 시작하고, 필요에 따라 복잡성 추가.** 초기에 25개 커맨드로 시작한 Huy Tieu가 결국 4개로 축소한 사례가 대표적.

2. **CLAUDE.md는 진화하는 문서.** okhlopkov의 경우 약 80줄까지 성장. 반복적 사용에서 발견된 엣지 케이스를 점진적으로 추가.

3. **index.md 전략이 80%의 핵심.** Michael Crist: "인덱스 파일이 80%의 작업을 한다. Claude Code가 모든 파일을 읽지 않고도 볼트를 탐색할 수 있게 해주는 지도."

4. **"에이전트는 읽고, 인간은 쓴다" 원칙.** AI 생성 텍스트를 볼트에 넣지 않거나, 별도 볼트/폴더에 격리.

5. **Git 기반 안전망.** Obsidian Git 플러그인 또는 Hooks의 자동 커밋으로 모든 변경사항 추적. 풀 리퀘스트 형태로 대규모 변경 검토.

6. **2단계 이하 폴더 깊이.** AI 탐색 효율과 토큰 비용을 위해 중첩 최소화. `Projects/Active/Q1/Research/Sources/topic.md` 대신 `Research/topic.md`.

### 7.2 피해야 할 함정

1. **과도한 구조화:** 과도한 폴더 중첩은 AI 탐색을 혼란스럽게 함
2. **전사 편집:** 음성 메모의 원본 텍스트를 수정하면 귀중한 원시 컨텍스트 손실
3. **불완전한 지침:** 모호한 CLAUDE.md 규칙은 AI가 의도를 추측하게 만듦
4. **버전 관리 누락:** 세션 후 자동 커밋 없으면 변경사항 추적 불가
5. **MCP 서버 과다:** 5개 이상의 MCP 서버는 토큰 소비로 비실용적
6. **자동화 의존:** 컨텍스트 파일은 정기 검토 없이 stale 해짐. 자동화가 수동 큐레이션을 완전히 대체하지 못함

### 7.3 시작 가이드 (30분)

```
1. Obsidian 설치, 새 볼트 생성 (5분)
2. 기본 폴더 구조 생성: inbox/, projects/, daily/, resources/, archive/ (5분)
3. CLAUDE.md 작성 (3가지 규칙: 일일 노트 위치, 태스크 저장소, 편집 제한) (5분)
4. Claude Code 설치: npm install -g @anthropic-ai/claude-code (2분)
5. obsidian-skills 설치: .claude 폴더에 복사 (3분)
6. 첫 테스트: "CLAUDE.md를 읽고 볼트 규칙을 요약해줘" (2분)
7. 두 번째 테스트: "모든 노트를 읽고 내가 보지 못한 연결을 찾아줘" (8분)
```

### 7.4 비용 참고

| 항목 | 비용 |
|------|------|
| Obsidian | 무료 |
| Claude Pro | $20/월 (기본 사용에 충분) |
| Claude Max | $100/월 (집중 사용 시 권장) |
| Obsidian Sync | $5/월 (선택) |
| 총 최소 비용 | $20/월 |

---

## 8. 출처 목록

### 공식 리소스
- [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) -- Obsidian CEO의 공식 Agent Skills (14.6k stars)
- [Steph Ango - How I Use Obsidian](https://stephango.com/vault) -- kepano의 볼트 사용법
- [kepano LinkedIn Post](https://www.linkedin.com/posts/stephango_if-youre-using-obsidian-with-claude-code-activity-7413195363395764224-NflB) -- 사용자 피드백 수집

### 스타터킷 및 템플릿
- [heyitsnoah/claudesidian](https://github.com/heyitsnoah/claudesidian) -- Claudesidian 스타터킷 (1,300+ stars)
- [ballred/obsidian-claude-pkm](https://github.com/ballred/obsidian-claude-pkm) -- AI Accountability System (1,181+ stars)
- [ashish141199/obsidian-claude-code](https://github.com/ashish141199/obsidian-claude-code) -- 미니멀 볼트 템플릿
- [hancengiz/cc-obsidian-vault-api-skill](https://github.com/hancengiz/cc-obsidian-vault-api-skill) -- REST API 기반 스킬

### MCP 서버 및 플러그인
- [smithery-ai/mcp-obsidian](https://github.com/smithery-ai/mcp-obsidian) -- Obsidian MCP 커넥터 (1.3k stars)
- [iansinnott/obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp) -- WebSocket MCP 서버
- [YishenTu/claudian](https://github.com/YishenTu/claudian) -- Obsidian 내 Claude Code 임베드 플러그인

### 심층 가이드
- [Michael Crist - Context Engineering](https://michaelcrist.substack.com/p/context-engineering) -- CLAUDE.md 전략
- [okhlopkov - Second Brain Setup Guide](https://okhlopkov.com/second-brain-obsidian-claude-code/) -- 완전한 설정 가이드
- [Kenneth Reitz - Obsidian Vaults & Claude Code](https://kennethreitz.org/essays/2026-03-06-obsidian_vaults_and_claude_code) -- 467 노트 볼트 사례
- [Chase Adams - AI-Native Obsidian Vault Setup Guide](https://curiouslychase.com/posts/ai-native-obsidian-vault-setup-guide/) -- 가장 상세한 구조 가이드
- [Nori Nishigaya - Claude Code and Obsidian Now Runs My Entire Day](https://emergentinsights.substack.com/p/claude-code-and-obsidian-now-runs) -- ADHD 최적화 워크플로우
- [Starmorph - Obsidian + Claude Code Integration Guide](https://blog.starmorph.com/blog/obsidian-claude-code-integration-guide) -- 5가지 연결 전략

### 개발자 사례
- [Damian Galarza - Complete Development Workflow](https://damiangalarza.com/posts/2025-11-25-how-i-use-claude-code/) -- Linear + Obsidian 통합
- [Stefan Imhoff - Agentic Note-Taking](https://www.stefanimhoff.de/agentic-note-taking-obsidian-claude-code/) -- 6,000 노트 재구성 사례
- [Kyle Gao - Using Claude Code with Obsidian](https://kyleygao.com/blog/2025/using-claude-code-with-obsidian/) -- 자동 백링킹

### 커뮤니티 & 미디어
- [Vibehackers - Building a Second Brain with Claude Code](https://vibehackers.io/blog/claude-code-second-brain) -- 종합 커뮤니티 리서치
- [Why Try AI - Build Your Second Brain](https://www.whytryai.com/p/claude-code-obsidian) -- 실용적 설정 가이드
- [dev.to - Claude Code Inside Obsidian](https://dev.to/numbpill3d/claude-code-inside-obsidian-the-setup-that-10xd-my-thinking-20e8) -- 기술적 구현
- [Eleanor Konik - Claude + Obsidian Got a Level Up](https://www.eleanorkonik.com/p/claude-obsidian-got-a-level-up) -- 15M 단어 볼트 사례
- [Teresa Torres - How to Choose Which Tasks to Automate](https://www.producttalk.org/how-to-choose-which-tasks-to-automate-with-ai/) -- 비기술자 워크플로우

### 동영상
- [Greg Isenberg & Internet Vin - How I Use Obsidian + Claude Code to Run My Life](https://www.youtube.com/watch?v=6MBq1paspVU) (178K views)
- [Mark Kashef - Claude Code Turned Obsidian Into My Dream Second Brain](https://www.youtube.com/watch?v=2kbINqpluM0)
- [CC For Everyone - Vin Obsidian Workflows (Interactive Lesson)](https://ccforeveryone.com/mini-lessons/vin-obsidian-workflows)

### Reddit / Forum
- [r/ObsidianMD - Yet another Claude-powered Second Brain](https://www.reddit.com/r/ObsidianMD/comments/1ruleg8/yet_another_claudepowered_second_brain_in/) -- PARA + Zettelkasten + 커스텀 Skills
- [r/ObsidianMD - How I Automated My Obsidian Workflow](https://www.reddit.com/r/ObsidianMD/comments/1on433j/how_i_automated_my_obsidian_workflow_with_claude/)
- [r/ClaudeAI - I used Obsidian as a persistent brain for Claude Code](https://www.reddit.com/r/ClaudeAI/comments/1rv5ox0/i_used_obsidian_as_a_persistent_brain_for_claude/)
- [Obsidian Forum - MCP Servers: Experiences and Recommendations](https://forum.obsidian.md/t/obsidian-mcp-servers-experiences-and-recommendations/99936)
- [Obsidian Forum - Agent Client Plugin](https://forum.obsidian.md/t/new-plugin-agent-client-bring-claude-code-codex-gemini-cli-inside-obsidian/108448)
