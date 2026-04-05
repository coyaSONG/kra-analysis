# `@repo/scripts` 개요

`packages/scripts`는 운영 API가 아니라 실험과 분석을 위한 Python 중심 스크립트 모음입니다. 평가, 프롬프트 개선, ML 실험, 자동 리서치 보조 로직이 여기에 있습니다.

## 현재 디렉터리 구조

```text
packages/scripts/
├─ evaluation/            # 평가, 리포트, leakage check
├─ prompt_improvement/    # 재귀 개선 및 분석
├─ ml/                    # 모델 학습/예측
├─ autoresearch/          # 자동 리서치 보조 로직
├─ shared/                # 공통 클라이언트와 DB 유틸
├─ tests/                 # pytest 기반 테스트
├─ archive/               # 과거 수집/전처리 실험 파일
├─ batch_collect_2025.py
├─ feature_engineering.py
└─ hybrid_predictor.py
```

중요: 오래된 문서에 나오는 `race_collector/`, 여러 Node 수집 스크립트, 예전 prompt evaluator 구조는 현재 기준 구조가 아닙니다. 관련 파일 상당수는 `archive/`로 이동했거나 삭제됐습니다.

## 주요 명령

저장소 루트에서 실행:

```bash
pnpm --filter=@repo/scripts run evaluate:help
pnpm --filter=@repo/scripts run evaluate:v3
pnpm --filter=@repo/scripts run improve:help
pnpm --filter=@repo/scripts run improve:v5
pnpm --filter=@repo/scripts run improve:analyze
pnpm --filter=@repo/scripts run lint
pnpm --filter=@repo/scripts run test
```

현재 `package.json` 기준 실제 스크립트는 다음과 같습니다.

- `evaluate:v3` -> `evaluation/evaluate_prompt_v3.py`
- `evaluate:predict-only` -> `evaluation/predict_only_test.py`
- `improve:v5` -> `prompt_improvement/recursive_prompt_improvement_v5.py`
- `improve:analyze` -> `prompt_improvement/analyze_enriched_patterns.py`

## 개발 메모

- 이 패키지는 별도 build step이 없습니다.
- lint와 test는 `uv` 기반 Python 실행을 사용합니다.
- 운영 수집은 현재 별도 Node collector 앱이 아니라 `apps/api`의 collection 엔드포인트 기준으로 보는 것이 맞습니다.

## 관련 문서

- [루트 README](/Users/chsong/Developer/Personal/kra-analysis/README.md)
- [프로젝트 개요](/Users/chsong/Developer/Personal/kra-analysis/docs/project-overview.md)
- [Knowledge Index](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/INDEX.md)
