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

## 공식 경기 목록 수집과 로컬 동결

전국 날짜별 목록과 지역별 목록 3개를 함께 저장하고, 전체 경주 키·출발 시각·출전 두수를 대조합니다. 영남 메뉴에는 부산경남과 영천이 함께 있으므로 실제 개최지를 경주 식별자로 사용합니다. API 키는 필요하지 않습니다.

저장소 루트에서 API 의존성이 설치된 Python으로 실행합니다.

```bash
PYTHONPATH=packages/scripts python -m autoresearch.kra_schedule_snapshot capture --output-dir .cache/autoresearch/forward-schedule
PYTHONPATH=packages/scripts python -m autoresearch.kra_schedule_snapshot audit --capture <capture.json> --race-date <YYYYMMDD>
PYTHONPATH=packages/scripts python -m autoresearch.kra_schedule_snapshot freeze --capture <capture.json> --race-date <YYYYMMDD> --output <new-universe.json>
```

`audit`은 원문 해시와 네 출처를 재검증하며, 불완전·불일치·미공표 상태에서는 종료 코드 2를 반환합니다. 미공표 날짜는 경주가 없는 날로 확정하지 않습니다. `freeze`는 해당 날짜의 첫 경주 30분 전보다 이른 시점에만 허용되며 기존 출력은 덮어쓰지 않습니다. 다른 날짜의 출처 충돌도 해결되기 전에는 동결하지 않습니다.

동결 출력은 `pending_independent_server_receipt`인 **로컬 후보**입니다. 로컬 시각과 HTTP Date는 독립적인 등록 증명이나 예측 성공률 근거가 아닙니다. 실제 미래 출전마 수집, 단일 예측 실행, 서버 시각 등록 및 결과 대조는 후속 단계입니다. [실제 원문 검증 기록](../../docs/research/2026-10-11-forward-race-universe.md)을 참고하세요.

## 말별 휴양 대용값 진단

`autoresearch.horse_entry_interval_audit`는 저장된 10월 검증 출전마 전체를 안정적인 말 ID로 과거 출전표와 연결합니다. `--dataset`, `--validation`, `--output`을 지정하며 기존 출력은 덮어쓰지 않습니다. 같은 날·미래 기록은 제외하고 이력이 없으면 null을 유지합니다.

출력 `days_since_prior_observed_entry`는 **관측된 이전 출전표와의 날짜 간격**이며 실제 출발 이력의 완전성이나 경주 전 가용성을 보증하지 않습니다. 기존 모델의 `rest_days`를 변경하거나 학습 승인에 쓰지 않습니다. 재현 명령과 실제 116경주 결과는 [휴양 대용값 연구 기록](../../docs/research/2026-10-11-horse-entry-interval-audit.md)에 있습니다.

## 관련 문서

- [루트 README](/Users/chsong/Developer/Personal/kra-analysis/README.md)
- [프로젝트 개요](/Users/chsong/Developer/Personal/kra-analysis/docs/project-overview.md)
- [Knowledge Index](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/INDEX.md)
