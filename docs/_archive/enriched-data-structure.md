# 보강된 데이터 구조 (Enriched Data Structure)

## 📋 개요

이 문서는 데이터 보강 시스템을 통해 생성되는 `_enriched.json` 파일의 상세 구조를 설명합니다.

## 🏗️ 전체 구조

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE."
    },
    "body": {
      "items": {
        "item": [
          {
            // 기본 정보 (API214_1)
            "hrName": "말이름",
            "hrNo": "말번호",
            "jkName": "기수이름",
            "jkNo": "기수번호",
            "trName": "조교사이름",
            "trNo": "조교사번호",
            
            // 보강된 정보
            "hrDetail": { /* 말 상세 */ },
            "jkDetail": { /* 기수 상세 */ },
            "trDetail": { /* 조교사 상세 */ }
          }
        ]
      }
    }
  }
}
```

## 📊 상세 필드 설명

### 1. 말 상세 정보 (hrDetail)

| 필드명 | 타입 | 설명 | 활용 방안 |
|--------|------|------|-----------|
| `faHrName` | string | 부마 이름 | 혈통 분석 |
| `faHrNo` | string | 부마 번호 | 부계 추적 |
| `moHrName` | string | 모마 이름 | 모계 분석 |
| `moHrNo` | string | 모마 번호 | 모계 추적 |
| `rcCntT` | number | 통산 출전 횟수 | 경험치 평가 |
| `ord1CntT` | number | 통산 1착 횟수 | 승률 계산 |
| `ord2CntT` | number | 통산 2착 횟수 | 복승률 계산 |
| `ord3CntT` | number | 통산 3착 횟수 | 연승률 계산 |
| `rcCntY` | number | 올해 출전 횟수 | 최근 활동량 |
| `ord1CntY` | number | 올해 1착 횟수 | 최근 폼 |
| `winRateT` | string | 통산 승률(%) | 능력 평가 |
| `plcRateT` | string | 통산 복승률(%) | 안정성 평가 |
| `winRateY` | string | 올해 승률(%) | 현재 폼 |
| `chaksunT` | number | 통산 상금(원) | 수익성 평가 |
| `rating` | number | 레이팅 | 능력 지표 |
| `hrLastAmt` | string | 최근 거래가 | 시장 가치 |

### 2. 기수 상세 정보 (jkDetail)

| 필드명 | 타입 | 설명 | 활용 방안 |
|--------|------|------|-----------|
| `age` | number | 기수 나이 | 경험/체력 평가 |
| `birthday` | string | 생년월일 | 나이 계산 |
| `debut` | string | 데뷔일 | 경력 계산 |
| `part` | string | 기수 구분 | 프리/소속 확인 |
| `ord1CntT` | number | 통산 1착 횟수 | 실력 평가 |
| `ord2CntT` | number | 통산 2착 횟수 | 안정성 평가 |
| `ord3CntT` | number | 통산 3착 횟수 | 꾸준함 평가 |
| `rcCntT` | number | 통산 출전 횟수 | 경험 평가 |
| `winRateT` | string | 통산 승률(%) | 기수 능력 |
| `plcRateT` | string | 통산 복승률(%) | 안정성 |
| `winRateY` | string | 올해 승률(%) | 현재 폼 |

### 3. 조교사 상세 정보 (trDetail)

| 필드명 | 타입 | 설명 | 활용 방안 |
|--------|------|------|-----------|
| `meet` | string | 소속 경마장 | 홈 어드밴티지 |
| `part` | number | 소속조 | 조직 규모 |
| `stDate` | number | 데뷔일 | 경력 평가 |
| `rcCntT` | number | 통산 출전 횟수 | 경험 평가 |
| `ord1CntT` | number | 통산 1착 횟수 | 조교 능력 |
| `winRateT` | number | 통산 승률(%) | 전체 실력 |
| `plcRateT` | number | 통산 복승률(%) | 안정성 |
| `qnlRateT` | number | 통산 연승률(%) | 상위권 진입력 |
| `winRateY` | number | 올해 승률(%) | 최근 성적 |
| `plcRateY` | number | 올해 복승률(%) | 최근 안정성 |

## 🎯 활용 전략

### 1. 신마 평가
```python
def evaluate_new_horse(horse):
    if horse['hrDetail']['rcCntT'] <= 3:
        # 혈통 중심 평가
        bloodline_score = analyze_bloodline(
            horse['hrDetail']['faHrName'],
            horse['hrDetail']['moHrName']
        )
        # 기수/조교사 실력으로 보완
        jockey_score = float(horse['jkDetail']['winRateT'])
        trainer_score = horse['trDetail']['winRateT']
```

### 2. 기수-말 궁합 분석
```python
def analyze_combination(horse):
    # 기수가 말보다 실력이 좋은 경우
    if float(horse['jkDetail']['winRateT']) > float(horse['hrDetail']['winRateT']):
        return "기수 어드밴티지"
    # 말이 기수보다 실력이 좋은 경우
    else:
        return "말 능력 의존"
```

### 3. 최근 폼 vs 통산 성적
```python
def analyze_form(detail, type='horse'):
    if type == 'horse':
        recent = float(detail['winRateY'])
        career = float(detail['winRateT'])
    elif type == 'jockey':
        recent = float(detail['winRateY'])
        career = float(detail['winRateT'])
    
    if recent > career * 1.2:
        return "상승세"
    elif recent < career * 0.8:
        return "하락세"
    else:
        return "평균 유지"
```

## 📈 데이터 품질 지표

### 완전성 체크
- `hrDetail`: 말 정보 존재 여부
- `jkDetail`: 기수 정보 존재 여부
- `trDetail`: 조교사 정보 존재 여부

### 신뢰도 평가
- 출전 횟수가 많을수록 통계 신뢰도 높음
- 최소 10회 이상 출전 시 의미 있는 승률
- 신마는 혈통 정보가 더 중요

## 🔗 관련 문서
- [데이터 보강 시스템](data-enrichment-system.md)
- [API 분석](api-analysis.md)
- [프롬프트 개발 전략](prompt-development-strategy.md)
