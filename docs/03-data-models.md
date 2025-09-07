# 데이터 모델 및 구조 (요약)

API v2에서 사용하는 핵심 데이터 모델 요약입니다. 세부 스키마는 코드(`apps/api/models/…`)와 보관 문서를 참고하세요.

## 주요 모델
- `CollectionRequest`
  - `date(YYYYMMDD)`, `meet(1~3)`, `race_numbers(선택)`, `options(enrich/get_results/force_refresh/parallel_count)`
- `CollectionResponse`
  - `status`, `message`, `data(선택)`, 비동기 시 `job_id`, `webhook_url`, `estimated_time`
- `CollectionStatus`
  - `date`, `meet`, `total_races`, `collected_races`, `enriched_races`, `status`, 타임스탬프 등
- `RaceData`
  - `race_id`, `race_info{rcDate,rcNo,rcName,rcDist,meet,…}`, `horses[]`, 수집/보강/결과 상태, 결과/타임스탬프
- `HorseData`
  - `chulNo`, `hrNo/hrName`, `age/sex`, `wgBudam`, `jkNo/jkName`, `trNo/trName`, `winOdds/plcOdds`, 보강 정보
- `Job`, `JobListResponse`, `JobDetailResponse`
  - 작업 타입/상태/진행률/타임스탬프/결과/태그 등

## 코드 참조
- `apps/api/models/collection_dto.py`
- `apps/api/models/job_dto.py`

## 보관 문서 (자세한 구조/배경)
- `_archive/data-structure.md`
- `_archive/enriched-data-structure.md`
- `_archive/prerace-data-structure.md`
- `_archive/data-enrichment-system.md`

