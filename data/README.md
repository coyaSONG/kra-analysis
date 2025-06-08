# Data 폴더 구조

## 📂 폴더 구조

```
data/
├── races/                 # 전처리된 경주 데이터
│   └── YYYY/MM/YYYYMMDD/
│       ├── seoul/        # 서울 경마장
│       ├── jeju/         # 제주 경마장
│       └── busan/        # 부산경남 경마장
│
├── prompt_evaluation/     # 프롬프트 평가 결과
├── full_evaluation/       # 전체 평가 결과
└── examples/             # API 응답 예시
```

## 📝 파일 명명 규칙

### 경주 파일
- 형식: `race_{경마장}_{날짜}_{경주번호}_prerace.json`
- 예시: `race_1_20250608_1_prerace.json` (서울 2025년 6월 8일 1경주)
- 위치: `data/races/2025/06/20250608/seoul/`

### 경마장 코드
- 1: 서울
- 2: 제주
- 3: 부산경남

## 🔄 데이터 흐름

1. **수집 & 전처리**: `collect_and_preprocess.js` 
   - API에서 데이터 수집
   - 즉시 전처리 (경주 전 상태로 변환)
   - 날짜/경마장별로 자동 정리하여 저장

2. **예측**: 전처리된 데이터로 프롬프트 실행

3. **평가**: `evaluate_prompt.py` → `prompt_evaluation/`

## 💡 핵심 특징

- **단순한 구조**: data 바로 아래 races 폴더
- **체계적 정리**: 날짜와 경마장별로 자동 분류
- **즉시 사용 가능**: 모든 데이터가 이미 전처리됨
- **경주 전 상태**: 모든 경주가 동일한 조건으로 표준화