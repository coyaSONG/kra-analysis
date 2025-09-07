# Claude Code를 통한 효과적인 프롬프트 전달 가이드

## 1. 메모리 기능 활용

### 1.1 CLAUDE.md 파일
프로젝트 루트에 `CLAUDE.md` 파일을 생성하여 프로젝트별 지시사항 저장:

```bash
# CLAUDE.md 초기화
claude
> /init
```

**CLAUDE.md 예시:**
```markdown
# 프로젝트 지침

## 코딩 컨벤션
- 변수명은 camelCase 사용
- 함수는 동사로 시작
- 테스트는 항상 작성

## 자주 사용하는 명령어
- 테스트: npm test
- 빌드: npm run build
- 배포: npm run deploy

## 프로젝트 구조
@CLAUDE.md 참조
```

### 1.2 빠른 메모리 추가
```bash
# 해시(#)로 시작하면 메모리에 추가
claude
> # 이 프로젝트에서는 항상 TypeScript를 사용하세요
```

### 1.3 파일 임포트
```markdown
# CLAUDE.md에서 다른 파일 참조
@package.json - 사용 가능한 npm 명령어
@docs/conventions.md - 코딩 규칙
@~/.claude/personal-preferences.md - 개인 설정
```

## 2. 프롬프트 전달 방식

### 2.1 대화형 모드
```bash
# 기본 대화 시작
claude

# 초기 프롬프트와 함께 시작
claude "이 프로젝트를 분석해주세요"
```

### 2.2 단일 명령 모드 (Print Mode)
```bash
# 단일 응답 받기
claude -p "이 함수의 목적을 설명하세요"

# 파일 내용과 함께
cat error.log | claude -p "이 오류를 분석하세요"
```

### 2.3 대화 이어가기
```bash
# 가장 최근 대화 계속
claude --continue
claude -c

# 특정 세션 재개
claude --resume abc123
```

## 3. 고급 프롬프트 기법

### 3.1 사고 모드 활성화
깊은 분석이 필요한 경우:
```bash
claude
> think about the best architecture for this payment system
> think harder about edge cases
> ultrathink  # 최고 수준의 사고 모드
```

### 3.2 시스템 프롬프트 커스터마이징
```bash
# 시스템 프롬프트 덮어쓰기 (--print 모드에서만)
claude -p "API 설계" --system-prompt "당신은 REST API 전문가입니다. 보안과 성능을 최우선으로 고려하세요."

# 시스템 프롬프트 추가
claude -p "코드 작성" --append-system-prompt "모든 코드 작성 후 반드시 자가 검토를 수행하세요."
```

### 3.3 프로젝트별 커스텀 명령어
```bash
# .claude/commands/optimize.md 생성
echo "이 코드의 성능을 분석하고 3가지 최적화 방안을 제시하세요:" > .claude/commands/optimize.md

# 사용
claude
> /project:optimize

# 인자와 함께 사용
> /project:fix-issue 123
```

## 4. 출력 형식 제어

### 4.1 JSON 출력
```bash
# 구조화된 JSON 응답
claude -p "함수 문서화" --output-format json

# 스트리밍 JSON
claude -p "앱 빌드" --output-format stream-json
```

### 4.2 프로그래밍 방식 활용
```bash
# JSON 파싱 예시
result=$(claude -p "코드 생성" --output-format json)
code=$(echo "$result" | jq -r '.result')
cost=$(echo "$result" | jq -r '.cost_usd')
```

## 5. 권한 및 자동화

### 5.1 특정 명령 자동 승인
```bash
# npm test 자동 승인
claude config add allowedTools "Bash(npm test)"

# npm test와 하위 명령 모두 승인
claude config add allowedTools "Bash(npm test:*)"
```

### 5.2 비대화형 모드 권한
```bash
# 권한 프롬프트 스킵 (주의!)
claude --dangerously-skip-permissions

# MCP 도구로 권한 처리
claude -p --permission-prompt-tool mcp_auth_tool "작업 수행"
```

## 6. 복잡한 프롬프트 구조화

### 6.1 XML 태그 활용 예시
```bash
claude -p "
<context>
프로젝트: 경마 예측 시스템
언어: Python
프레임워크: FastAPI
</context>

<task>
삼복연승 예측 API 엔드포인트 생성
</task>

<requirements>
- 입력 검증
- 에러 처리
- 문서화
</requirements>
"
```

### 6.2 Chain of Thought 유도
```bash
claude -p "
이 문제를 단계별로 해결하세요:

<steps>
1. 현재 구조 분석
2. 문제점 식별
3. 해결 방안 도출
4. 구현 계획 수립
</steps>

각 단계마다 <reasoning> 태그로 사고 과정을 표시하세요.
"
```

## 7. 세션 관리

### 7.1 세션 저장 및 재사용
```bash
# 세션 ID 저장
claude -p "프로젝트 초기화" --output-format json | jq -r '.session_id' > session.txt

# 세션 재개
claude -p --resume "$(cat session.txt)" "테스트 추가"
```

### 7.2 대화 기록 관리
```bash
# 대화 목록 보기
claude --resume  # 인터랙티브 선택

# 자동 압축 설정
claude
> /config  # 자동 대화 압축 토글
```

## 8. 파이프라인 통합

### 8.1 스크립트에서 활용
```bash
#!/bin/bash

# 에러 처리와 함께
if ! claude -p "$prompt" 2>error.log; then
    echo "오류 발생:" >&2
    cat error.log >&2
    exit 1
fi

# 타임아웃 설정
timeout 300 claude -p "$complex_prompt" || echo "5분 후 타임아웃"
```

### 8.2 빌드 프로세스 통합
```json
// package.json
{
  "scripts": {
    "lint:claude": "claude -p 'main 브랜치 대비 변경사항을 검토하고 타입 오류나 버그를 찾아주세요. 파일명과 라인 번호를 포함해서 간결하게 보고하세요.'"
  }
}
```

## 9. 디버깅 및 모니터링

### 9.1 상세 로깅
```bash
# 전체 대화 과정 보기
claude --verbose

# MCP 디버그 모드
claude --mcp-debug
```

### 9.2 텔레메트리 설정
```bash
# 텔레메트리 활성화
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# OTLP 설정
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## 10. 경마 예측 프로젝트 적용 예시

### 10.1 CLAUDE.md 설정
```markdown
# 경마 예측 프로젝트

## 프로젝트 개요
한국마사회(KRA) 경마 데이터를 분석하여 삼복연승을 예측하는 시스템

## 중요 지침
- 시장 평가 가중치는 20% 이상 유지
- 데이터 부족 말은 배당률 중심으로 평가
- 체중 변화는 맥락을 고려하여 해석

## 프롬프트 템플릿
@prompts/prediction-template-v2.md

## 데이터 구조
@docs/data-structure.md

## 분석 가이드라인
@docs/prompt-improvement-analysis.md
```

### 10.2 예측 실행 명령
```bash
# 구조화된 프롬프트로 예측
claude -p "
<race_data>
$(cat data/raw/races/test_race_3_20250523_1.json)
</race_data>

<analysis_steps>
@prompts/prediction-template-v2.md
</analysis_steps>

<output_format>
JSON 형식으로 예측 결과 제공
</output_format>
"
```

### 10.3 커스텀 명령어 설정
```bash
# .claude/commands/predict.md
echo "
주어진 경주 데이터를 분석하여 삼복연승을 예측하세요.
다음 단계를 따르세요:
1. 데이터 검증
2. 각 말 개별 분석
3. 종합 점수 계산
4. 상위 3마리 선정
5. 신뢰도 평가
" > .claude/commands/predict.md

# 사용
claude
> /project:predict
```

## 모범 사례 요약

1. **프로젝트별 CLAUDE.md 활용** - 반복되는 지침 저장
2. **구조화된 프롬프트** - XML 태그로 명확한 구조 제공
3. **적절한 모드 선택** - 대화형 vs 단일 명령 모드
4. **세션 관리** - 복잡한 작업은 세션 저장/재개
5. **자동화 설정** - 반복 작업은 권한 사전 승인
6. **커스텀 명령어** - 자주 사용하는 프롬프트 템플릿화
7. **사고 모드 활용** - 복잡한 문제는 think 키워드 사용
8. **출력 형식 지정** - 프로그래밍 연동 시 JSON 활용
