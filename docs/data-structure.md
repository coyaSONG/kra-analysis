# 데이터 저장 및 관리 구조 설계

## 디렉토리 구조

```
kra-analysis/
├── data/
│   ├── raw/              # API에서 받은 원본 데이터
│   │   ├── races/        # 경주 정보
│   │   ├── horses/       # 말 정보
│   │   ├── jockeys/      # 기수 정보
│   │   └── results/      # 경주 결과
│   ├── processed/        # 분석용으로 가공된 데이터
│   │   ├── pre-race/     # 경주 전 데이터 (예측용)
│   │   └── post-race/    # 경주 후 데이터 (검증용)
│   └── predictions/      # 예측 결과 저장
│       ├── prompts/      # 사용된 프롬프트
│       ├── results/      # 예측 결과
│       └── analysis/     # 분석 리포트
├── scripts/              # 데이터 처리 스크립트
│   ├── collect_data.py   # API 데이터 수집
│   ├── process_data.py   # 데이터 가공
│   └── analyze_results.py # 결과 분석
└── tests/                # 테스트 데이터 및 스크립트
```

## 데이터 파일 명명 규칙

### 1. 원본 데이터 (raw/)
```
{api_name}_{meet}_{date}_{race_no}.json
예: api214_3_20250606_1.json
```

### 2. 가공 데이터 (processed/)
```
race_{meet}_{date}_{race_no}_prerace.json   # 경주 전 데이터
race_{meet}_{date}_{race_no}_postrace.json  # 경주 후 데이터
```

### 3. 예측 결과 (predictions/)
```
prediction_{meet}_{date}_{race_no}_{timestamp}.json
```

## 데이터 구조 정의

### 1. 경주 전 데이터 구조 (pre-race)
```json
{
  "race_info": {
    "meet": "부경",
    "meet_code": "3",
    "race_date": "20250606",
    "race_no": 1,
    "distance": 1200,
    "track_condition": "건조 (2%)",
    "weather": "흐림",
    "race_name": "일반",
    "age_condition": "연령오픈",
    "prize_condition": "R0~0"
  },
  "horses": [
    {
      "chul_no": 1,
      "hr_no": "0051228",
      "hr_name": "올라운드원",
      "age": 3,
      "sex": "거",
      "weight": "511(+2)",
      "rank": "국6등급",
      "rating": 0,
      "jockey": {
        "jk_no": "080565",
        "jk_name": "정도윤",
        "weight": 57,
        "win_rate_total": 15.5,
        "win_rate_year": 14.2,
        "recent_stats": {
          "races": 415,
          "wins": 59,
          "seconds": 48,
          "thirds": 40
        }
      },
      "trainer": {
        "tr_no": "070180",
        "tr_name": "안우성",
        "win_rate_total": 18.2,
        "win_rate_year": 16.5
      },
      "recent_races": [
        {
          "date": "20250523",
          "position": 1,
          "distance": 1200,
          "time": 75.4,
          "track": "건조"
        }
      ],
      "odds": {
        "win": 3.0,
        "place": 1.2
      }
    }
  ],
  "collected_at": "2025-06-06T10:00:00Z"
}
```

### 2. 예측 결과 구조
```json
{
  "race_id": "3_20250606_1",
  "prediction": {
    "selected_horses": [
      {"chul_no": 3, "hr_name": "올라운드원", "score": 85.5},
      {"chul_no": 7, "hr_name": "파워풀킹", "score": 82.3},
      {"chul_no": 5, "hr_name": "골든레이서", "score": 78.9}
    ],
    "confidence": "상",
    "analysis_points": {
      "horse_1": ["최근 3경주 연속 상위권", "기수 승률 높음"],
      "horse_2": ["동일 거리 강세", "체중 안정적"],
      "horse_3": ["조교사 성적 우수", "상승세"]
    }
  },
  "prompt_used": "initial-prediction-template-v1.0",
  "predicted_at": "2025-06-06T11:00:00Z",
  "model": "claude-3-opus"
}
```

### 3. 결과 분석 구조
```json
{
  "race_id": "3_20250606_1",
  "actual_result": {
    "1st": {"chul_no": 3, "hr_name": "올라운드원"},
    "2nd": {"chul_no": 5, "hr_name": "골든레이서"},
    "3rd": {"chul_no": 10, "hr_name": "스피드마스터"}
  },
  "prediction_result": {
    "hit_type": "부분적중",
    "correct_horses": 2,
    "accuracy_score": 66.7,
    "details": "예측한 3마리 중 2마리(3번, 5번)가 1-3위 내 포함"
  },
  "improvement_notes": [
    "10번 말의 막판 추입력을 과소평가",
    "7번 말의 주로 상태 부적응 미고려"
  ],
  "analyzed_at": "2025-06-06T18:00:00Z"
}
```

## 데이터 관리 원칙

1. **버전 관리**: 모든 예측과 분석 결과는 타임스탬프와 함께 저장
2. **무결성**: 원본 데이터(raw)는 수정하지 않고 보존
3. **추적성**: 각 예측에 사용된 프롬프트 버전 기록
4. **재현성**: 동일한 입력 데이터로 예측 재현 가능
5. **보안**: .env 파일과 API 키는 절대 커밋하지 않음

## 현재 실제 구조 (2025-06-22 업데이트)

실제 구현에서는 다음과 같은 구조를 사용하고 있습니다:

```
data/
├── cache/
│   ├── horses/                    # 말 상세정보 캐시 (hrNo.json)
│   └── results/                   # 경주 결과 (top3_날짜_경마장_경주.json)
├── races/                         # 원본 경주 데이터
│   └── YYYY/MM/YYYYMMDD/meet/    # 연도/월/날짜/경마장별 분류
│       ├── race_*_prerace.json   # 경주 전 데이터
│       └── race_*_enriched.json  # 상세정보 포함 데이터
├── prompt_evaluation/             # 프롬프트 평가 결과
├── prediction_tests/              # 예측 테스트 결과
└── recursive_improvement_v5/       # v5 재귀 개선 시스템 결과
```

### 핵심 파일 형태

**경주 결과 (cache/results/)**:
```json
[6, 7, 1]  // 1위: 6번, 2위: 7번, 3위: 1번
```

**enriched 데이터**: 기존 경주 데이터 + 말/기수/조교사 상세정보 통합

### 데이터 수집 도구

- `get_race_result.js`: 개별 경주 결과 수집
- `collect_and_preprocess.js`: 경주 전 데이터 수집
- `enrich_race_data.js`: 상세정보 추가