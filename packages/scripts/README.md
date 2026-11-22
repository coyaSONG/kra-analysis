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

## 전체 경주표의 제한된 API26 수집

`autoresearch.kra_entry_scope_intake`는 한 주간의 공식 전국표와 지역표 원본이
모두 일치하는 경우에만 날짜·실제 경마장별 기존 API26 수집기를 실행합니다.
날짜는 원본에 나온 전체 날짜를 오름차순으로 지정합니다. 먼저 호출 없는
`plan`으로 예상 페이지 수와 최초 마감 시각을 확인합니다.

```bash
PYTHONPATH=packages/scripts python -m autoresearch.kra_entry_scope_intake plan \
  --schedule-capture <capture.json> --schedule-sha256 <sha256> \
  --date <YYYYMMDD> --date <YYYYMMDD>
```

실제 수집은 고정한 경주표에 `collect`를 실행하고 `--first-cutoff <시각>`
(시간대가 있는 ISO 8601), `--max-requests <한도>`, `--api-key-file <키-파일>`,
`--output-dir .cache/autoresearch/api26-scope-intake`를 추가합니다.
이미 보존된 원본에는 `--reuse-entry <entry_capture.json> <sha256>`를 지정할 수
있습니다. 완전한 해당 범위를 재현하면 그 범위는 호출하지 않습니다.
동일한 출력 폴더에서 겹치는 날짜를 다시 예약할 수 없습니다.

마감은 최초 고정한 전체표의 첫 출발 30분 전입니다. 제출한 표로 계산한 마감이
이미 고정한 시각과 다르면 예약이나 호출 없이 중단합니다. 첫 수집 실패에서도
추가 호출을 중단하고 인증 오류·접근 거부·호출 제한·빈 응답을 구분합니다.
빈 응답이나 미시도 범위를
경주 없음으로 집계하지 않습니다. 보존된 원본·예약·수집 기록은 로컬 자료이며
등록, 마감 전 공개 증명 또는 예측이 아닙니다.

마감 전, 완료된 `receipt.json` 및 SHA256과 처음 고정한 전체 경주표의 SHA256,
최초 마감 시각을 별도로 넘겨 모델 입력을 확인합니다. 접수 기록에 새로 적힌
값으로 원래 기준을 바꾸지 않습니다. 예약·전체 경주표·원본 페이지를 다시 읽고
기존 M0 입력 변환기로 모든 경주를 확인합니다. API27도 이 데이터를 공유합니다. 날짜·경주·원본 핀과
특성별 누락 수가 포함된 로컬 입력을 반환하며 추가 호출이나 파일 변경은 없습니다.

```bash
PYTHONPATH=packages/scripts python -m autoresearch.kra_entry_scope_inputs \
  --receipt <receipt.json> --receipt-sha256 <sha256> \
  --schedule-sha256 <frozen-schedule-sha256> --first-cutoff <시각>
```

원본 불일치, 해석할 수 없는 특성, 또는 마감 경과 시 부분 입력을 내보내지
않습니다. `verified_local_inputs_only`는 예측 실행, 승인, 등록이나 공개를
의미하지 않으며 이전 구간의 입력 예약을 대체하지 않습니다.

## 전체 경주표 입력의 마감 전 존재 증명

같은 전체표와 접수 기록으로 마감 **전** `stage`를 실행하면 접수 기록 옆에
`whole-card-input-packet.json`을 한 번만 생성합니다. 이 비공개 묶음은
전국·지역 경주표와 API26 원본의 해시를 간접적으로 고정하고, 전체 경주의
공통 모델 입력 해시와 특성별 누락 수를 보존합니다. 표준 출력은 공개 가능한
두 필드의 JSON만 담습니다.

```bash
PYTHONPATH=packages/scripts python -m autoresearch.kra_entry_scope_witness stage \
  --receipt <receipt.json> --receipt-sha256 <sha256> \
  --schedule-sha256 <frozen-schedule-sha256> --first-cutoff <시각>
```

승인된 절차로 표준 출력의 정확한 바이트만
`docs/research/input-witnesses/<packet_sha256>.json`으로 만들어 일반 PR로
`main`에 병합합니다. 원본·비공개 묶음·말 식별자·모델 입력은 공개하지
않습니다. 이 명령은 PR을 열거나 제출하지 않습니다.

병합 이후 같은 네 인수와 `--packet-sha256 <packet_sha256> --pull <PR번호>`를
사용해 `capture`를 실행합니다. 원본을 재현한 뒤 GitHub에서 PR과 병합
커밋의 정확한 공개 문서를 한 번씩 읽고 응답을 접수 기록 옆에 보존합니다.
같은 인수의 `replay`는 추가 호출이나 파일 변경 없이 검증합니다.
마감과 같은 시각 또는 이후에 병합되면 종료 코드 2로 남기며 소급 승인하지
않습니다. 게이트나 요청에 문제가 생겨도 같은 증명 폴더를 덮어쓰지 않습니다.

정상 검증은 해당 해시의 내용이 마감 전에 존재했다는 증거입니다. GitHub가
KRA 원본을 인증하거나 정확한 수집 시각을 보증한다는 뜻은 아닙니다.
학습 승인, 전체 평가 등록 및 마감 전 예측 공개는 여전히 별도 절차입니다.

## 별도 사전 승인 전체표의 고정 M0/API27 예측

10월 16~18일 계약은 그대로입니다. 이 명령은 그 모집단이나 이미 놓친
마감을 다시 열지 않습니다. 새 전체 경주표의 입력 해시가 마감 전에 공개되고
해당 GitHub 응답까지 수집된 경우에만 준비합니다. 임의 날짜나 경주 수를 직접
입력해 등록하지 않습니다.

`autoresearch.fixed_pair_forward`의 모든 하위 명령은 `--study`,
`--receipt`, `--receipt-sha256`를 받습니다. `prepare`에는 원래
`--schedule-sha256`, `--first-cutoff`, 비공개 `--packet-sha256`,
입력 해시 공개 `--input-pull`, 미리 열어 둔 소유자의 예측
`--prediction-pull`, 소유자가 지정한 별개 GitHub 계정 `--reviewer`와
`--analysis <file.json>`을 넘깁니다. 분석 JSON은 `horizon`, `uncertainty`,
`sample_size_rationale`, `stopping`의 네 항목을 구체적 문장으로 고정합니다.
`prepare`는 로컬 JSON만 출력하며 등록이나 승인, 모델 실행이 아닙니다.

소유자가 그 정확한 프로토콜을 `docs/research/protocols/fixed-pair-v1/<study>.json`
으로 일반 병합합니다. 지정 검토자는 원본·전체 모집단·분석 계획과 필수 검사
근거를 독립적으로 확인한 뒤, 별도 PR에
`docs/research/approvals/fixed-pair-v1/<study>.json`을 게시합니다.
승인 문서에는 `format_version: kra-fixed-pair-prospective-approval-v1`,
`study_id`, `protocol_sha256`, `protocol_pr`, `reviewer`, 시간대가
있는 `reviewed_at`, 그리고 실제 확인한 경우에만 `source_closure_reviewed`,
`population_and_statistics_reviewed`, `release_checks_reviewed`를
JSON 참으로 적습니다. 두 문서는 키 정렬, 두 칸 들여쓰기, 마지막 개행이
있는 기존 JSON 형식입니다. 문서가 있다는 사실만으로는 승인되지 않습니다.

마감 전에 소유자 프로토콜과 독립 승인 문서가 담긴 `main`을 가져온 분리
체크아웃에서 `run --protocol-pull <번호> --approval-pull <번호>`를
실행합니다. `run` 및 이후 명령에는 기존 불변 산출물 경로
`--m0-model-dir`, `--api27-model-dir`도 넘깁니다. 모델 해시와 적합 기록이
다르면 허용하지 않습니다. 실행은 원래 날짜 전체를 공용 Git 디렉터리에서
한 번만 예약하고, 두 공개 문서와 미리 연 예측 PR을 새로 확인합니다.
승인이 다르거나 마감을 넘기면 재실행 없이 실패를 보존합니다.

`verify`는 저장된 정확한 출력을 읽기 전용으로 재현합니다. `stage`는 마감
전에만 같은 예측 바이트를 출력합니다. 이 바이트만
`docs/research/commitments/fixed-pair-v1/<study>/paired.json`으로,
처음 고정한 PR에서 일반 병합합니다. `witness`는 그 정확한 문서와 병합
시각을 한 번 읽고, `replay-witness`는 보존된 응답으로 다시 확인합니다.
두 명령은 마감 이후에도 실제 병합 시각을 검증할 수 있습니다. 한 모델의
명시적 미제출도 경주를 지우지 않으며, 아직 확인하지 않은 결과는 실패나
적중률 0이 아닙니다. 이 명령은 재학습하거나 결과를 수집·평가하지 않습니다.

## 새 고정 모델 쌍의 공식 결과 비교

이 명령은 위의 별도 승인 예측 형식만 읽습니다. 기존 10월 16~18일
공개 예측과 `api27_evaluation`은 그대로입니다.

```bash
PYTHONPATH=packages/scripts python -B -m autoresearch.fixed_pair_evaluation \
  --study <id> --receipt <receipt.json> --receipt-sha256 <sha256> \
  --protocol-pull <번호> --protocol-sha256 <sha256> \
  --approval-pull <번호> --approval-sha256 <sha256> \
  --pair-sha256 <sha256> --m0-model-dir <dir> --api27-model-dir <dir> \
  --outcome-plan <outcome-plan.json> --outcome-sha256 <sha256>
```

승인과 공개 원본은 원래 실행 기록에서 읽습니다. 별도로 이미 수집한
동일 형식의 증거 폴더는 `--authority-dir`로 지정할 수 있습니다.
결과 계획에는 사후 경주표 대신 **처음 동결한 경주표의 정확한 해시**와
보존한 API214·공식 HTML 버전이 있어야 합니다. 결과 계획이나 예측 공개
증거가 없으면 해당 인수는 생략하고 미확인으로 남깁니다. 정확한 시각의
공개가 확인돼도 원래 모델·환경에서 수치 재현이 되지 않으면 적중·실패로
처리하지 않습니다. 원본 실행 환경을 보관하고, 이후 코드를 바꿨다면
원래 작업 환경의 `PYTHONPATH`로 이 평가 파일을 별도 경로에서 실행할 수
있습니다.

명령은 추가 요청이나 파일 쓰기 없이 JSON을 출력합니다. 공식 정정을
비교할 때는 `--prior-outcome-plan`과 `--prior-outcome-sha256`로 이전
원본 버전도 고정합니다. 예측과 모집단은 그대로 두고 두 결과 버전을
대조합니다. 대기·목표 미정의 또는 모집단 충돌이 있으면 전체 정확도·우열은
비워 두며, 거리·등급·경마장별 숫자는 진단용 건수로만 보고합니다.

## 말별 휴양 대용값 진단

`autoresearch.horse_entry_interval_audit`는 저장된 10월 검증 출전마 전체를 안정적인 말 ID로 과거 출전표와 연결합니다. `--dataset`, `--validation`, `--output`을 지정하며 기존 출력은 덮어쓰지 않습니다. 같은 날·미래 기록은 제외하고 이력이 없으면 null을 유지합니다.

출력 `days_since_prior_observed_entry`는 **관측된 이전 출전표와의 날짜 간격**이며 실제 출발 이력의 완전성이나 경주 전 가용성을 보증하지 않습니다. 기존 모델의 `rest_days`를 변경하거나 학습 승인에 쓰지 않습니다. 재현 명령과 실제 116경주 결과는 [휴양 대용값 연구 기록](../../docs/research/2026-10-11-horse-entry-interval-audit.md)에 있습니다.

## 공식 결과 원문 수집

`autoresearch.kra_result_snapshot`은 API214의 개최장·날짜 전체 페이지를 저장합니다. 순위 필터 없이 취소·제외·중지·불성립 행도 보존합니다. API 키는 파일에서 읽으며 출력과 원문 묶음에 기록하지 않습니다.

```bash
PYTHONPATH=packages/scripts python -m autoresearch.kra_result_snapshot capture --meet <1..4> --race-date <YYYYMMDD> --api-key-file <secret-file> --output-dir .cache/autoresearch/prior-results
PYTHONPATH=packages/scripts python -m autoresearch.kra_result_snapshot audit --capture <capture.json>
PYTHONPATH=packages/scripts python -m autoresearch.kra_result_population_audit --plan <pinned-plan.json> --output <new-audit.json>
```

결과 원문에 개최지가 없으면 요청 파라미터만으로 채우지 않습니다. `audit`에 `--entry-capture <entry_capture.json> --archive-root <archive-root>`를 추가하면 검증된 API26 날짜 전체 원문과 경주·출주번호·안정 말 ID를 양방향 대조합니다. 경주 후 두수가 다른 명부는 식별자 대조에만 사용할 수 있으며 사전 명부 적격성이 되지 않습니다.

수집·재생 성공은 실제 출발 이력 완전성이나 독립적인 시각 증명이 아닙니다. 대사 보고서는 누락·추가 경주와 두수 불일치를 남기며, 불일치가 있으면 종료 코드 2를 반환합니다. 과거 자료의 당일 수집은 과거 PIT 승인이나 70% 성능 근거가 아닙니다. 계획 형식과 실제 원문 해시는 [결과 수집 연구 기록](../../docs/research/2026-10-11-prior-result-capture.md)을 참고하세요.

각 경주의 `top3_observation`은 순위·말 ID 중복, 순위 누락, 미해결 상태와 두수 불일치를 별도로 검사합니다. `candidate_top3_horse_ids`는 순서 무관 관측 후보일 뿐 공식 확정 결과가 아니며, `requires_review` 경주도 전체 목록에 남습니다. 종료 코드는 기존 두수 대사 기준을 유지하므로 코드 0만으로 결과 확정을 판단하지 마세요. [50경주 상위 3두 관측 기록](../../docs/research/2026-10-11-result-top3-readiness.md)에 재현 결과와 한계가 있습니다.

## 관련 문서

- [루트 README](/Users/chsong/Developer/Personal/kra-analysis/README.md)
- [프로젝트 개요](/Users/chsong/Developer/Personal/kra-analysis/docs/project-overview.md)
- [Knowledge Index](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/INDEX.md)
