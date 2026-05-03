# 재현성 체크 실행 런북 v1

이 문서는 `ralph` 기반 KRA 예측 연구/운영 파이프라인에서 재현성 체크를 반복 실행하는 표준 절차를 정의한다. 목표는 다음 3가지를 고정하는 것이다.

- 최근 기간 홀드아웃/`mini_val` 경계와 경주 목록이 동일 입력에서 항상 동일하게 재생성되는지 확인
- `research_clean.py` 평가 결과가 동일 snapshot, 동일 config, 동일 모델 난수 조건에서 다시 실행해도 동일하게 재현되는지 확인
- 운영 승인 전 재현성 체크 결과를 같은 형식의 로그로 남겨 실패 원인과 후속 조치를 추적 가능하게 만드는 것

이 문서는 실제 코드 계약과 연결된다.

- 홀드아웃 규칙: [docs/recent-holdout-split-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md)
- 홀드아웃 스냅샷 포맷: [docs/holdout-snapshot-filtering-format.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-snapshot-filtering-format.md)
- 홀드아웃 재생성 체크 구현: [packages/scripts/autoresearch/holdout_split.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/holdout_split.py)
- 평가 결과 manifest 구현: [packages/scripts/autoresearch/reproducibility.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/reproducibility.py)
- 연구 평가 실행기: [packages/scripts/autoresearch/research_clean.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/research_clean.py)

## 1. 언제 실행하나

아래 시점에는 반드시 1회 이상 실행한다.

- 홀드아웃 snapshot 또는 split manifest를 새로 생성한 직후
- `clean_model_config.json` 또는 `research_clean.py`를 바꾼 직후
- `ralph` 탐색 결과를 운영 후보로 승격하기 직전
- 새 경주 결과 누적으로 자동 재학습 체계를 갱신한 뒤 운영 승인 직전

## 2. 선행 조건

- 작업 디렉터리는 저장소 루트여야 한다.
- `uv` 의존성이 설치되어 있어야 한다.
- `packages/scripts/autoresearch/snapshots/` 아래의 `holdout.json`, `holdout_answer_key.json`, `mini_val.json`, `mini_val_answer_key.json` 이 최신 상태여야 한다.
- 운영 판단 기준의 시간순 홀드아웃 구간은 [docs/recent-holdout-split-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md) 와 일치해야 한다.

## 3. 표준 실행 절차

### 3-1. 계약 테스트 실행

먼저 split 재생성과 manifest 스키마 계약이 깨지지 않았는지 확인한다.

```bash
uv run pytest -q packages/scripts/autoresearch/tests/test_holdout_split.py
uv run pytest -q packages/scripts/autoresearch/tests/test_prepare.py -k reproducibility
uv run pytest -q packages/scripts/autoresearch/tests/test_reproducibility_manifest.py
uv run pytest -q packages/scripts/tests/test_holdout_split_manifest_schema.py
```

### 3-2. 실산출물 2회 재실행 체크

동일 config로 `research_clean.py`를 두 번 실행해 결과 JSON이 동일한지 확인한다. companion manifest는 실행 시각이 들어가므로 byte-level 동일성을 요구하지 않고, invariant 필드만 비교한다.

```bash
rm -rf .tmp/repro-check
mkdir -p .tmp/repro-check/run_a .tmp/repro-check/run_b

uv run python packages/scripts/autoresearch/research_clean.py \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output .tmp/repro-check/run_a/research_clean.json

uv run python packages/scripts/autoresearch/research_clean.py \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output .tmp/repro-check/run_b/research_clean.json
```

다음 명령으로 결과와 manifest invariant를 함께 점검하고, 사람이 검수할 수 있는 JSON/Markdown 리포트를 남긴다.

```bash
uv run python -m autoresearch.reproducibility \
  --reference-output .tmp/repro-check/run_a/research_clean.json \
  --regenerated-output .tmp/repro-check/run_b/research_clean.json \
  --report-dir .tmp/repro-check
```

이 명령은 아래 파일을 생성한다.

- `.tmp/repro-check/research_evaluation_reproducibility_report.json`
- `.tmp/repro-check/research_evaluation_reproducibility_report.md`

리포트에는 다음이 포함된다.

- required check 기준의 일치/불일치 항목
- 각 비교 대상의 SHA-256 해시와 byte size
- 첫 차이 경로를 포함한 차이 요약
- run A / run B의 `summary`, `integrity`, `source_data.version_id`

### 3-3. `ralph` 실험 출력 최소 게이트 확인

`ralph` 실험 출력이 운영 금지 조건을 밟지 않았는지 확인한다.

```bash
uv run python packages/scripts/autoresearch/extract_rrx_metric.py
```

이 명령은 다음 조건 중 하나라도 위반되면 `0` 을 출력한다.

- `integrity.all_missing_features` 가 비어 있지 않음
- `integrity.normalized_first3_match_rate > 0.05`
- `market_feature_count > 0`

즉, `0` 이 나오면 성능 수치 이전에 입력/누수/결측 조건부터 다시 확인해야 한다.

## 4. 기대 결과

### 4-1. 계약 테스트

- 위 4개 pytest 명령이 모두 `passed` 여야 한다.
- 특히 `test_holdout_manifest_reproducibility_is_input_order_invariant` 와 `test_check_manifest_reproducibility_reports_identical_regeneration` 이 통과해야 한다.
- `test_reproducibility_manifest.py` 는 평가 결과 bundle이 companion manifest를 저장하고 schema 검증을 통과하는지 보장해야 한다.

### 4-2. 실산출물 비교

- `research_clean.json` 은 run A / run B가 완전히 동일해야 한다.
- 두 run의 `summary.robust_exact_rate`, `summary.rolling_min_exact_rate`, `summary.overfit_safe_exact_rate` 가 동일해야 한다.
- 두 run의 `integrity.all_missing_features` 는 빈 배열이어야 한다.
- 두 run의 `market_feature_count` 는 `0` 이어야 한다.
- 두 run의 manifest에서 아래 필드는 동일해야 한다.
  - `source_data.version_id`
  - `configuration.config_sha256`
  - `configuration.settings`
  - `seeds`
  - `artifacts` 중 입력 계열(`input_config`, `input_dataset`, `input_answer_key`)의 hash와 byte size

### 4-3. 홀드아웃 안정성 계약

- `holdout_split_manifest.json` 의 `metadata.seed.selection_seed_invariant` 는 `true` 여야 한다.
- `metadata.seed.evaluation_seeds` 는 10개여야 하며 현재 기본값은 `(11, 17, 23, 31, 37, 41, 47, 53, 59, 61)` 이다.
- 동일 홀드아웃 날짜 구간에서 최종 성공 판정은 10개 시드 결과의 최저 상위 3두 무순서 적중률이 `0.70` 이상일 때만 `PASS` 로 기록한다.

주의: 현재 워크트리의 자동 재현성 체크는 split 고정성과 단일 `model_random_state=42` 평가 재실행까지를 직접 보장한다. 10개 시드 반복 성능 floor는 별도 반복 평가 실행 결과를 로그에 반드시 첨부해야 하며, 값이 비어 있으면 운영 승인 불가로 본다.

## 5. 실패 시 점검 항목

### 5-1. 계약 테스트 실패

- `packages/scripts/autoresearch/holdout_split.py` 에서 `included_race_ids` 정렬 순서가 바뀌지 않았는지 확인
- `manifest_created_at` 를 고정하지 않은 테스트/스크립트가 섞이지 않았는지 확인
- `packages/scripts/shared/holdout_split_manifest_schema.py` 와 실제 payload 필드가 어긋나지 않았는지 확인
- snapshot 생성 규칙 변경이 [docs/recent-holdout-split-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md) 와 일치하는지 확인

### 5-2. `research_clean.json` 2회 실행 결과 불일치

- `research_clean.py` 에서 모델 `random_state` 가 고정값(`42`)인지 확인
- tie-break, 정렬, group 순회 순서가 입력 순서에 의존하지 않는지 확인
- `clean_model_config.json` 이 두 실행 사이에 변경되지 않았는지 확인
- snapshot 파일이 두 실행 사이에 덮어써지지 않았는지 확인
- feature 생성 로직이 현재 시각, 파일 시스템 순서, dict 순서 등에 의존하지 않는지 확인

### 5-3. manifest invariant 불일치

- `source_data.version_id` 가 달라졌다면 `holdout.json` 또는 `holdout_answer_key.json` hash가 바뀐 것이다. snapshot 재생성 여부를 먼저 확인
- `configuration.config_sha256` 가 달라졌다면 config drift다. 승인되지 않은 실험 config가 섞였는지 확인
- `seeds` 가 달라졌다면 `holdout_split_manifest.json` 또는 모델 난수 정책이 변한 것이다
- 입력 artifact hash가 달라졌다면 `.tmp/repro-check` 이전에 원본 snapshot이 갱신되었는지 확인

### 5-4. `extract_rrx_metric.py` 가 `0` 출력

- `integrity.all_missing_features` 의 필드명이 whitelist 밖 신규 feature인지 확인
- `normalized_first3_match_rate` 가 0.05를 넘으면 결과 데이터/정답키 누수 가능성을 우선 의심
- `market_feature_count > 0` 이면 `winOdds`, `plcOdds`, `odds_rank`, `winOdds_rr`, `plcOdds_rr` 가 config에 섞였는지 확인

### 5-5. 10시드 floor 미달 또는 미기록

- 홀드아웃 구간과 평가 경주 목록이 모든 시드에서 동일했는지 먼저 확인
- 시드별로 바뀐 항목이 모델 내부 난수 외에 없는지 확인
- 최저 성능 run의 config SHA, snapshot version, feature set이 나머지 9개와 같은지 확인
- 최저 성능이 `0.70` 미만이면 운영 승인 대신 연구 후보 상태로 되돌리고 실패 원인을 별도 기록

## 6. 실행 로그 템플릿

아래 템플릿을 운영 점검 로그나 PR 코멘트에 그대로 붙여 사용한다.

```md
# 재현성 체크 로그

- 실행 시각:
- 실행자:
- 브랜치/커밋:
- 목적: 운영 승인 전 / snapshot 재생성 후 / config 변경 후 / 기타

## 입력 기준

- config 경로: `packages/scripts/autoresearch/clean_model_config.json`
- holdout snapshot version:
- holdout answer key hash:
- holdout split manifest SHA:
- evaluation_seeds:

## 실행 명령

- [ ] `uv run pytest -q packages/scripts/autoresearch/tests/test_holdout_split.py`
- [ ] `uv run pytest -q packages/scripts/autoresearch/tests/test_prepare.py -k reproducibility`
- [ ] `uv run pytest -q packages/scripts/autoresearch/tests/test_reproducibility_manifest.py`
- [ ] `uv run pytest -q packages/scripts/tests/test_holdout_split_manifest_schema.py`
- [ ] `uv run python packages/scripts/autoresearch/research_clean.py --config packages/scripts/autoresearch/clean_model_config.json --output .tmp/repro-check/run_a/research_clean.json`
- [ ] `uv run python packages/scripts/autoresearch/research_clean.py --config packages/scripts/autoresearch/clean_model_config.json --output .tmp/repro-check/run_b/research_clean.json`
- [ ] 결과/manifest invariant 비교 스크립트 실행
- [ ] `uv run python packages/scripts/autoresearch/extract_rrx_metric.py`

## 기대 결과 대비 실제 결과

- 계약 테스트 전체 통과 여부:
- `research_clean.json` run A/B 동일 여부:
- manifest invariant 동일 여부:
- `integrity.all_missing_features`:
- `market_feature_count`:
- `summary.robust_exact_rate`:
- `summary.rolling_min_exact_rate`:
- `summary.overfit_safe_exact_rate`:
- 10시드 최저 상위 3두 무순서 적중률:
- 운영 승인 판정: PASS / FAIL / HOLD

## 실패 또는 이슈

- 증상:
- 최초 확인 지점:
- 원인 가설:
- 재실행 여부:
- 후속 조치:
```
