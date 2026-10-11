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

## 운영 모델 학습 승인

`ml/train_clean.py`는 경주 전 원본과 피처 생성 근거를 검토한 정확한 입력 묶음만 학습합니다. `data/contracts/production_training_reviews_v1.json`의 승인 목록은 현재 비어 있습니다. 기존 2025 legacy bootstrap 자료는 오프라인 진단에는 사용할 수 있지만 운영 학습에는 사용할 수 없습니다. 시간 필드나 `passed=true`를 추가하는 것만으로 승인되지 않습니다.

설정·데이터·정답·매니페스트는 한 번 읽은 바이트로 검증하고 학습합니다. 승인에는 변환 코드, 계약, 잠금 파일, 실행 환경과 소스 검토 문서의 해시도 묶습니다. 입력을 승인하려면 실제 원본 수집·공개 버전, 피처별 과거 시점 근거, 조인·전체 출전마 검토를 완료한 뒤 별도 PR로 추가해야 합니다.

기본 출력은 `models/candidate_clean.joblib`입니다. 기존 출력 파일은 교체하지 않으며 챔피언 자동 승격도 하지 않습니다. 자세한 승인 기준과 실제 자료 감사는 [학습 증거 연구 기록](../../docs/research/2026-10-11-production-training-evidence.md)을 참고하세요.

후보와 함께 `.joblib.receipt.json` 완료 기록을 저장합니다. 실제 학습 행렬·정답·가중치·출전마 순서·학습 집합 및 모델 파일 해시가 연결됩니다. 모델과 완료 기록이 모두 존재하고 모델 해시가 일치해야 완료로 취급합니다. 저장 중단으로 기록만 남은 경우에는 자동 덮어쓰기 없이 원인을 확인해야 합니다.

## 관련 문서

- [루트 README](/Users/chsong/Developer/Personal/kra-analysis/README.md)
- [프로젝트 개요](/Users/chsong/Developer/Personal/kra-analysis/docs/project-overview.md)
- [Knowledge Index](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/INDEX.md)
