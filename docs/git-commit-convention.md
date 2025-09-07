# Git Commit Convention

이 프로젝트는 **Conventional Commits** 규칙을 따릅니다.

## 커밋 메시지 구조

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Type (필수)

- **feat**: 새로운 기능 추가
- **fix**: 버그 수정
- **docs**: 문서만 변경
- **style**: 코드 의미에 영향을 주지 않는 변경 (공백, 포맷팅, 세미콜론 등)
- **refactor**: 버그 수정이나 기능 추가가 아닌 코드 변경
- **perf**: 성능 개선
- **test**: 누락된 테스트 추가 또는 기존 테스트 수정
- **chore**: 빌드 프로세스 또는 보조 도구 및 라이브러리 변경
- **ci**: CI 설정 파일 및 스크립트 변경
- **revert**: 이전 커밋 되돌리기

## Scope (선택)

커밋이 영향을 미치는 범위를 명시합니다.

예시:
- `feat(auth): add login feature`
- `fix(api): resolve timeout issue`
- `docs(readme): update installation guide`

## Description (필수)

- 명령형, 현재 시제 사용 ("change" not "changed" or "changes")
- 첫 글자 소문자
- 마침표(.) 없음
- 50자 이내

## Body (선택)

- 무엇을, 왜 변경했는지 설명
- 명령형, 현재 시제 사용
- 이전 동작과 새로운 동작의 대비 설명

## Footer (선택)

- **BREAKING CHANGE**: 주요 변경사항
- **Fixes**: 해결한 이슈 (예: `Fixes #123`)
- **Refs**: 참조 이슈 (예: `Refs #456`)

## 예시

### 기본 커밋
```
feat: add user authentication
```

### Scope 포함
```
fix(api): handle null response from weather service
```

### 상세 설명 포함
```
feat(race-collector): implement retry mechanism for API calls

Add exponential backoff retry logic to handle temporary API failures.
This improves data collection reliability by retrying failed requests
up to 3 times with increasing delays.

Fixes #45
```

### Breaking Change
```
feat(evaluation): change evaluation API to use enriched data

- Change evaluate_prompt() signature to accept enriched_data parameter
- Remove support for basic data format
- Update all evaluation scripts to use new API

BREAKING CHANGE: evaluate_prompt() now requires enriched_data parameter.
Old basic data format is no longer supported.
```

### 여러 이슈 참조
```
fix(prompt): resolve JSON parsing errors in v10 prompts

- Add proper error handling for malformed JSON
- Validate prompt output before parsing
- Add retry logic for parsing failures

Fixes #123, #124
Refs #100
```

## 커밋하기 전 체크리스트

1. [ ] Type이 적절한가?
2. [ ] Scope가 명확한가? (필요한 경우)
3. [ ] Description이 명확하고 간결한가?
4. [ ] Body에 충분한 컨텍스트를 제공했는가? (필요한 경우)
5. [ ] Breaking changes가 있다면 명시했는가?
6. [ ] 관련 이슈를 참조했는가?

## 자주 하는 실수

❌ **나쁜 예시:**
```
update stuff
fix
WIP
misc changes
fix bug
```

✅ **좋은 예시:**
```
fix(auth): resolve token expiration issue
feat(prompt): add v10.3 with composite scoring
docs(readme): update performance metrics
refactor(evaluation): extract common validation logic
```

## 팁

1. 커밋은 하나의 논리적 변경사항만 포함
2. 커밋 메시지로 코드 리뷰가 가능할 정도로 명확하게
3. 나중에 `git log`로 찾기 쉽도록 검색 가능한 키워드 사용
4. 팀원이 이해할 수 있는 용어 사용