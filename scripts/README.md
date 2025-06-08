# Scripts 폴더 구조

## 📂 폴더 구조

```
scripts/
├── race_collector/          # 경주 데이터 수집 및 전처리
│   ├── collect_and_preprocess.js    # 메인 수집/전처리 통합 스크립트 ⭐
│   ├── smart_preprocess_races.py    # 스마트 전처리 모듈
│   ├── preprocess_race_data_v2.py   # 전처리 핵심 로직
│   └── verify_data_consistency.py   # 데이터 일관성 검증
│
├── prompt_evaluator/        # 프롬프트 평가 (준비 중)
│
├── archive/                 # 구버전 및 미사용 스크립트 보관
│
├── evaluate_prompt.py              # 프롬프트 성능 평가
├── recursive_prompt_improvement.py # 재귀적 프롬프트 개선
├── evaluate_all_races.py          # 전체 경주 평가
├── analyze_and_improve_prompt.py  # 프롬프트 분석 및 개선
└── evaluate_prompt_debug.py       # 디버그용 평가

```

## 🚀 주요 사용법

### 1. 경주 데이터 수집 및 전처리
```bash
# 오늘 서울 경마장 데이터 수집
node scripts/race_collector/collect_and_preprocess.js

# 특정 날짜와 경마장 지정
node scripts/race_collector/collect_and_preprocess.js 20250607 2

# 경마장 코드: 1=서울, 2=제주, 3=부산경남
```

### 2. 데이터 검증
```bash
# 전처리된 데이터 일관성 확인
python3 scripts/race_collector/verify_data_consistency.py
```

### 3. 프롬프트 평가
```bash
# 특정 프롬프트 버전 평가
python3 scripts/evaluate_prompt.py v9.0 prompts/prediction-template-v9.0-final.md 30

# 전체 경주로 평가
python3 scripts/evaluate_all_races.py prompts/prediction-template-v9.0-final.md v9.0

# 재귀적 개선
python3 scripts/recursive_prompt_improvement.py
```

## 📋 작업 흐름

1. **데이터 수집**: `race_collector/collect_and_preprocess.js`로 경주 데이터 수집
2. **데이터 확인**: `race_collector/verify_data_consistency.py`로 일관성 검증
3. **예측 실행**: 프롬프트를 사용하여 예측
4. **성능 평가**: `evaluate_prompt.py`로 정확도 측정
5. **개선**: `recursive_prompt_improvement.py`로 프롬프트 최적화