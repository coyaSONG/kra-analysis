# Scripts 폴더 구조

## 📂 현재 폴더 구조

```
scripts/
├── evaluation/              # 평가 시스템 ⭐
│   ├── evaluate_prompt_v3.py     # 최신 평가 시스템 (Claude Code CLI 최적화)
│   ├── evaluate_prompt_v2.py     # 이전 버전 (enriched 데이터 지원)
│   └── fetch_and_save_results.js # 경주 결과 가져오기 (Node.js)
│
├── race_collector/          # 경주 데이터 수집 및 처리 ⭐
│   ├── collect_and_preprocess.js    # API214_1 데이터 수집
│   ├── enrich_race_data.js         # 말/기수/조교사 상세정보 추가
│   ├── api_clients.js              # API8_2, API12_1, API19_1 클라이언트
│   ├── smart_preprocess_races.py    # 스마트 전처리
│   ├── preprocess_race_data_v2.py   # 전처리 핵심 로직
│   ├── verify_data_consistency.py   # 데이터 일관성 검증
│   └── retry_failed_enrichment.js   # 실패한 보강 재시도
│
├── prompt_improvement/      # 프롬프트 개선 도구
│   ├── recursive_prompt_improvement.py  # 재귀적 프롬프트 개선
│   └── analyze_and_improve_prompt.py   # 프롬프트 분석 및 개선
│
├── prompt_evaluator/        # (준비 중)
│
└── archive/                 # 미사용/구버전 파일
    ├── old_evaluation/      # 구버전 평가 스크립트
    ├── failed_attempts/     # SSL 문제 등으로 실패한 시도
    └── test_files/          # 임시 테스트 파일
```

## 🚀 주요 사용법

### 1. 경주 데이터 수집 및 처리

```bash
# 기본 데이터 수집 (API214_1)
node scripts/race_collector/collect_and_preprocess.js 20250608 1

# 데이터 보강 (말/기수/조교사 상세정보 추가)
node scripts/race_collector/enrich_race_data.js 20250608 1

# 데이터 검증
python3 scripts/race_collector/verify_data_consistency.py
```

### 2. 프롬프트 평가

```bash
# 최신 평가 시스템 사용 (v3 - Claude Code CLI 최적화)
python3 scripts/evaluation/evaluate_prompt_v3.py v10.0 prompts/prediction-template-v10.0.md 30 3

# 파라미터 설명:
# - v10.0: 프롬프트 버전
# - prompts/...: 프롬프트 파일 경로
# - 30: 테스트할 경주 수
# - 3: 병렬 실행 수
```

### 3. 프롬프트 개선

```bash
# 재귀적 개선 프로세스
python3 scripts/prompt_improvement/recursive_prompt_improvement.py

# 평가 결과 분석 및 개선안 도출
python3 scripts/prompt_improvement/analyze_and_improve_prompt.py
```

## 📋 표준 작업 흐름

1. **데이터 수집**
   ```bash
   node scripts/race_collector/collect_and_preprocess.js 20250608 1
   ```

2. **데이터 보강**
   ```bash
   node scripts/race_collector/enrich_race_data.js 20250608 1
   ```

3. **프롬프트 평가**
   ```bash
   python3 scripts/evaluation/evaluate_prompt_v3.py v10.0 prompts/v10.0.md 30
   ```

4. **결과 분석 및 개선**
   ```bash
   python3 scripts/prompt_improvement/analyze_and_improve_prompt.py
   ```

## 🔧 환경 설정

### 필수 환경 변수 (.env)
```
KRA_SERVICE_KEY=your_api_key_here
```

### Python 패키지
```bash
pip install -r requirements.txt
```

### Node.js 패키지
```bash
npm install node-fetch dotenv
```

## 📊 출력 데이터 구조

- **수집 데이터**: `data/races/YYYY/MM/DD/venue/*_prerace.json`
- **보강 데이터**: `data/races/YYYY/MM/DD/venue/*_enriched.json`
- **평가 결과**: `data/prompt_evaluation/evaluation_*.json`
- **경주 결과**: `data/cache/results/top3_*.json`
- **API 캐시**: `data/cache/{horses,jockeys,trainers}/*.json`