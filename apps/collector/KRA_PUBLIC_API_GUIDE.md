# 한국마사회(KRA) 공공 API 사용 가이드

## 📖 개요

한국마사회(KRA)에서 공공데이터포털(data.go.kr)을 통해 제공하는 경마 관련 공공 API의 완전한 사용 가이드입니다. 이 프로젝트에서 실제 사용하고 검증된 API들을 중심으로 작성되었습니다.

---

## 🔑 사전 준비사항

### 1. 서비스 키 발급
1. [공공데이터포털](https://data.go.kr) 회원가입
2. "한국마사회" 검색
3. 필요한 API 서비스 신청
4. 승인 후 서비스키 발급받기

### 2. 환경변수 설정
```bash
export KRA_SERVICE_KEY="your_service_key_here"
```

### 3. 표기/인코딩 주의
- 엔드포인트별 서비스키 파라미터 명칭이 상이합니다. 일부는 `serviceKey`, 일부는 `ServiceKey`를 사용합니다. 본 문서의 각 API 섹션 표에 명시된 실제 명칭을 그대로 사용하세요.
- 한글 파라미터(예: `jk_name`, `hr_name`, `tr_name`)는 URL 인코딩이 필요합니다.
  - 예: `const q = encodeURIComponent('김용근'); const url = \`...&jk_name=${q}\``

---

## 🌐 API 목록

총 5개의 API가 제공됩니다:
1. **API214_1** - 경주 상세 결과 조회
2. **API299** - 경주결과 종합 (통계용)
3. **API12_1** - 기수 정보 조회
4. **API8_2** - 경주마 상세정보
5. **API19_1** - 조교사 상세정보

### 1. API214_1 - 경주 상세 결과 조회

**API 이름**: 한국마사회 경마시행당일 경주결과 상세  
**Base URL**: `https://apis.data.go.kr/B551015/API214_1`  
**엔드포인트**: `/RaceDetailResult_1`
**HTTP 메서드**: GET

#### 📋 요청 파라미터
| 파라미터명 | 필수여부 | 타입 | 설명 | 예시 |
|-----------|---------|------|------|------|
| serviceKey | O | string | 서비스 인증키 | 발급받은 키 |
| numOfRows | O | string | 결과 수 | "50" |
| pageNo | O | string | 페이지 번호 | "1" |
| meet | X | string | 경마장 (1:서울, 2:제주, 3:부산) | "1" |
| rc_date | X | string | 경주일자 (YYYYMMDD) | "20250606" |
| rc_no | X | string | 경주번호 | "1" |

#### 🔗 요청 URL 예시
```
# JSON 응답 (추천)
https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey={KEY}&numOfRows=50&pageNo=1&meet=1&rc_date=20250606&rc_no=1&_type=json

# XML 응답 (기본값)
https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey={KEY}&numOfRows=50&pageNo=1&meet=1&rc_date=20250606&rc_no=1
```

#### 📊 응답 데이터 구조

**말(Horse) 관련 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `hrName` | string | 말 이름 | "올라운드원" |
| `hrNo` | string | 말 등록번호 | "0051228" |
| `age` | number | 말 연령 | 3 |
| `sex` | string | 말 성별 (수/암/거) | "거" |
| `birthday` | string | 말 생년월일 (YYYYMMDD) | "20220303" |
| `wgHr` | string | 마체중 (변화량 포함) | "511(+2)" |
| `rank` | string | 말 등급 | "국6등급" |
| `rankRise` | number | 등급 변화 | 0 |
| `hrTool` | string | 마구 정보 | "망사,반가지큰,승인편자+,혀끈-" |

**기수(Jockey) 관련 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `jkName` | string | 기수 이름 | "정도윤" |
| `jkNo` | string | 기수 번호 | "080565" |
| `wgJk` | number | 기수 중량 | 0 |

**조교사(Trainer) 관련 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `trName` | string | 조교사 이름 | "안우성" |
| `trNo` | string | 조교사 번호 | "070180" |

**마주(Owner) 관련 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `owName` | string | 마주 이름 | "김혜진" |
| `owNo` | string | 마주 번호 | "118011" |

**경주(Race) 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `rcDate` | string | 경주일자 (YYYYMMDD) | "20250523" |
| `rcDay` | string | 요일 | "금요일" |
| `rcNo` | number | 경주번호 | 1 |
| `rcName` | string | 경주명 | "일반" |
| `rcDist` | number | 경주거리(m) | 1200 |
| `rcTime` | number | 경주기록(초) | 75.4 |
| `meet` | string | 경마장 | "부경" |
| `track` | string | 주로 상태 | "건조 (2%)" |
| `weather` | string | 날씨 | "흐림" |

**경주 결과 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `ord` | number | 착순 | 1 |
| `ordBigo` | string | 착순 비고 | "-" |
| `chulNo` | number | 출주번호 | 10 |
| `diffUnit` | string | 착차 | "-" |

**배당률 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `winOdds` | number | 단승 배당률 | 3.0 |
| `plcOdds` | number | 복승 배당률 | 1.2 |

**상금 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `chaksun1` | number | 1착 상금(원) | 16500000 |
| `chaksun2` | number | 2착 상금(원) | 6600000 |
| `chaksun3` | number | 3착 상금(원) | 4200000 |
| `chaksun4` | number | 4착 상금(원) | 1500000 |
| `chaksun5` | number | 5착 상금(원) | 1200000 |

**부담중량 관련 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `wgBudam` | number | 부담중량(kg) | 57 |
| `wgBudamBigo` | string | 부담중량 비고 | "-" |
| `budam` | string | 부담 구분 | "별정A" |

**구간 기록 필드 (부산경남 기준)**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `buS1fTime` | number | 첫 1F 기록 | 14.1 |
| `buS1fAccTime` | number | 첫 1F 누적시간 | 14.1 |
| `buS1fOrd` | number | 첫 1F 순위 | 6 |
| `bu_1fGTime` | number | 1F 구간시간 | 13.0 |
| `bu_2fGTime` | number | 2F 구간시간 | 25.4 |
| `bu_3fGTime` | number | 3F 구간시간 | 37.9 |
| `bu_4_2fTime` | number | 4-2F 구간시간 | 24.5 |
| `bu_6_4fTime` | number | 6-4F 구간시간 | 25.5 |
| `buG1fAccTime` | number | G1F 누적시간 | 62.4 |
| `buG1fOrd` | number | G1F 순위 | 2 |
| `buG2fAccTime` | number | G2F 누적시간 | 50.0 |
| `buG2fOrd` | number | G2F 순위 | 5 |

**경주 조건 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `ageCond` | string | 연령 조건 | "연령오픈" |
| `prizeCond` | string | 상금 조건 | "R0~0" |
| `ilsu` | number | 간격일수 | 39 |
| `rating` | number | 레이팅 | 0 |

**기타 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `name` | string | 국가 | "한국" |
| `buga1` | number | 부가1 | 0 |
| `buga2` | number | 부가2 | 0 |
| `buga3` | number | 부가3 | 0 |

#### ✅ 검증된 사용 사례
```javascript
// Node.js 예시 (JSON 사용 - 추천)
const response = await fetch(
  `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${apiKey}&numOfRows=50&pageNo=1&meet=3&rc_date=20250606&rc_no=1&_type=json`
);
const jsonData = await response.json();
// 바로 사용 가능, XML 파싱 불필요

// 또는 XML 사용
const xmlResponse = await fetch(
  `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${apiKey}&numOfRows=50&pageNo=1&meet=3&rc_date=20250606&rc_no=1`
);
const xmlText = await xmlResponse.text();
// XML 파싱 필요
```

---

### 2. API299 - 경주결과 종합 (통계용)

**API 이름**: 한국마사회 경마시행당일 경주결과 종합  
**Base URL**: `https://apis.data.go.kr/B551015/API299`  
**엔드포인트**: `/Race_Result_total`
**HTTP 메서드**: GET

#### 📋 요청 파라미터
| 파라미터명 | 필수여부 | 타입 | 설명 | 예시 |
|-----------|---------|------|------|------|
| serviceKey | O | string | 서비스 인증키 | 발급받은 키 |
| pageNo | O | string | 페이지 번호 | "1" |
| numOfRows | O | string | 결과 수 | "10" |
| meet | X | string | 경마장 | "1" |
| rc_year | X | string | 경주 년도 (YYYY) | "2025" |
| rc_month | X | string | 경주 년월 (YYYYMM) | "202506" |
| rc_date | X | string | 경주 일자 (YYYYMMDD) | "20250606" |
| rc_no | X | string | 경주 번호 | "1" |

#### 🔗 요청 URL 예시
```
# JSON 응답 (추천)
https://apis.data.go.kr/B551015/API299/Race_Result_total?serviceKey={KEY}&pageNo=1&numOfRows=10&rc_date=20250503&_type=json

# XML 응답 (기본값)
https://apis.data.go.kr/B551015/API299/Race_Result_total?serviceKey={KEY}&pageNo=1&numOfRows=10&rc_date=20250503
```

#### 📊 응답 데이터 구조

**말(Horse) 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `hrName` | string | 말 이름 | "올라운드원" |
| `hrNo` | string | 말 등록번호 | "0051228" |
| `hrOrd1CntT` | string | 말 통산 1착 횟수 | "3" |
| `hrOrd2CntT` | string | 말 통산 2착 횟수 | "2" |
| `hrOrd3CntT` | string | 말 통산 3착 횟수 | "1" |
| `hrRcCntT` | string | 말 총 출전 횟수 | "15" |
| `hrOrd1CntY` | string | 말 올해 1착 횟수 | "1" |
| `hrOrd2CntY` | string | 말 올해 2착 횟수 | "1" |
| `hrOrd3CntY` | string | 말 올해 3착 횟수 | "0" |
| `hrRcCntY` | string | 말 올해 출전 횟수 | "5" |

**기수(Jockey) 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `jkName` | string | 기수 이름 | "정도윤" |
| `jkNo` | string | 기수 번호 | "080565" |
| `jkOrd1CntT` | string | 기수 통산 1착 횟수 | "45" |
| `jkOrd2CntT` | string | 기수 통산 2착 횟수 | "38" |
| `jkOrd3CntT` | string | 기수 통산 3착 횟수 | "33" |
| `jkRcCntT` | string | 기수 통산 출전 횟수 | "320" |
| `jkOrd1CntY` | string | 기수 올해 1착 횟수 | "12" |
| `jkOrd2CntY` | string | 기수 올해 2착 횟수 | "10" |
| `jkOrd3CntY` | string | 기수 올해 3착 횟수 | "8" |
| `jkRcCntY` | string | 기수 올해 출전 횟수 | "85" |
| `jkAge` | string | 기수 나이 | "28" |
| `jkCareer` | string | 기수 경력 | "5년" |

**조교사(Trainer) 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `trName` | string | 조교사 이름 | "안우성" |
| `trNo` | string | 조교사 번호 | "070180" |
| `trOrd1CntT` | string | 조교사 통산 1착 횟수 | "67" |
| `trOrd2CntT` | string | 조교사 통산 2착 횟수 | "52" |
| `trOrd3CntT` | string | 조교사 통산 3착 횟수 | "48" |
| `trRcCntT` | string | 조교사 통산 출전 횟수 | "445" |
| `trOrd1CntY` | string | 조교사 올해 1착 횟수 | "15" |
| `trOrd2CntY` | string | 조교사 올해 2착 횟수 | "13" |
| `trOrd3CntY` | string | 조교사 올해 3착 횟수 | "11" |
| `trRcCntY` | string | 조교사 올해 출전 횟수 | "120" |

**경주(Race) 기본 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `rcDate` | string | 경주일자 (YYYYMMDD) | "20250523" |
| `rcNo` | string | 경주번호 | "1" |
| `meet` | string | 경마장 코드 | "3" |
| `chulNo` | string | 출주번호 | "10" |
| `ord` | string | 최종 착순 | "1" |
| `rcTime` | string | 경주 기록(초) | "75.4" |

**기타 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `rcCntT` | string | 총 경주 출전 횟수 | "15" |
| `ord1CntT` | string | 총 1착 횟수 | "3" |
| `winRate` | string | 승률(%) | "20.0" |
| `placeRate` | string | 연대율(%) | "40.0" |

#### ✅ 검증된 사용 사례
```javascript
// 기수 승률 계산 예시 (실제 데이터 기반)
const jockeyWinRateTotal = (968 / 6254) * 100;  // 15.5% 통산 승률
const jockeyWinRateThisYear = (59 / 415) * 100; // 14.2% 올해 승률

// 기수 연대율 계산
const jockeyPlaceRate = ((968 + 791 + 685) / 6254) * 100; // 39.0% 연대율

// 기수 경력 계산 (2025년 기준)
const careerYears = 2025 - parseInt('20050504'.slice(0, 4)); // 20년 경력
```

---

### 3. API12_1 - 기수 정보 조회

**API 이름**: 한국마사회 기수정보 조회  
**Base URL**: `https://apis.data.go.kr/B551015/API12_1`  
**엔드포인트**: `/jockeyInfo_1`
**HTTP 메서드**: GET

#### 📋 요청 파라미터
| 파라미터명 | 필수여부 | 타입 | 설명 | 예시 |
|-----------|---------|------|------|------|
| serviceKey | O | string | 서비스 인증키 | 발급받은 키 |
| numOfRows | O | string | 결과 수 | "100" |
| pageNo | O | string | 페이지 번호 | "1" |
| jk_name | X | string | 기수명 | "김용근" |
| jk_no | X | string | 기수번호 | "080405" |
| meet | X | string | 경마장 | "1" |

#### 🔗 요청 URL 예시
```
# JSON 응답 (추천)
https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1?serviceKey={KEY}&numOfRows=100&pageNo=1&jk_name=김용근&_type=json

# XML 응답 (기본값)
https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1?serviceKey={KEY}&numOfRows=100&pageNo=1&jk_name=김용근
```

#### 📊 응답 데이터 구조

**기수 기본 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `jkName` | string | 기수명 (한글) | "김용근" |
| `jkNo` | string | 기수번호 | "080405" |
| `meet` | string | 소속 경마장명 | "서울" |
| `age` | string | 기수 나이 | "43" |
| `birthday` | string | 기수 생년월일 (YYYYMMDD) | "19820212" |
| `debut` | string | 데뷔 일자 (YYYYMMDD) | "20050504" |
| `part` | string | 기수 구분 | "프리기수" |

**기수 성적 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `ord1CntT` | string | 통산 1착 횟수 | "968" |
| `ord2CntT` | string | 통산 2착 횟수 | "791" |
| `ord3CntT` | string | 통산 3착 횟수 | "685" |
| `rcCntT` | string | 통산 총 출전 횟수 | "6254" |
| `ord1CntY` | string | 올해 1착 횟수 | "59" |
| `ord2CntY` | string | 올해 2착 횟수 | "48" |
| `ord3CntY` | string | 올해 3착 횟수 | "40" |
| `rcCntY` | string | 올해 총 출전 횟수 | "415" |

**기수 체중 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `wgPart` | string | 파트 기수 체중(kg) | "51" |
| `wgOther` | string | 기타 체중(kg) | "51" |
| `spDate` | string | 특별 일자 | "-" |

---

### 4. API8_2 - 경주마 상세정보

**API 이름**: 한국마사회 경주마 상세정보  
**Base URL**: `https://apis.data.go.kr/B551015/API8_2`  
**엔드포인트**: `/raceHorseInfo_2`
**HTTP 메서드**: GET

#### 📋 요청 파라미터
| 파라미터명 | 필수여부 | 타입 | 설명 | 예시 |
|-----------|---------|------|------|------|
| ServiceKey | O | string | 서비스 인증키 | 발급받은 키 |
| pageNo | O | string | 페이지번호 | "1" |
| numOfRows | O | string | 한 페이지 결과 수 | "10" |
| hr_name | X | string | 마명 | "올라운드원" |
| hr_no | X | string | 마번 | "0051228" |
| meet | X | string | 시행경마장구분 (1:서울, 2:제주, 3:부산) | "1" |
| act_gubun | X | string | 현역경주마여부 ('y':현역만, 기본값) | "y" |
| _type | X | string | 데이터형식구분 | "json" |

#### 🔗 요청 URL 예시
```
# JSON 응답 (추천)
https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey={KEY}&pageNo=1&numOfRows=10&hr_name=올라운드원&_type=json

# XML 응답 (기본값)
https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey={KEY}&pageNo=1&numOfRows=10&hr_name=올라운드원
```

#### 📊 응답 데이터 구조

**말 기본 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `hrName` | string | 마명 | "올라운드원" |
| `hrNo` | string | 마번 | "0051228" |
| `name` | string | 출생국가 | "한국" |
| `sex` | string | 성별 (수/암/거) | "거" |
| `birthday` | number | 생년월일 (YYYYMMDD) | 20220303 |
| `rank` | string | 등급 | "국5" |
| `meet` | string | 시행경마장명 | "부산경남" |

**조교사 및 마주 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `trName` | string | 조교사명 | "안우성" |
| `trNo` | string | 조교사번호 | "070180" |
| `owName` | string | 마주명 | "김혜진" |
| `owNo` | number | 마주번호 | 118011 |

**혈통 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `faHrName` | string | 부마명 | "사이먼퓨어" |
| `faHrNo` | string | 부마번호 | "0031261" |
| `moHrName` | string | 모마명 | "모닝퀸" |
| `moHrNo` | string | 모마번호 | "0031853" |

**성적 통계 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `rcCntT` | number | 통산총출주회수 | 2 |
| `ord1CntT` | number | 통산1착회수 | 1 |
| `ord2CntT` | number | 통산2착회수 | 0 |
| `ord3CntT` | number | 통산3착회수 | 0 |
| `rcCntY` | number | 최근1년총출주회수 | 2 |
| `ord1CntY` | number | 최근1년1착회수 | 1 |
| `ord2CntY` | number | 최근1년2착회수 | 0 |
| `ord3CntY` | number | 최근1년3착회수 | 0 |

**기타 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `chaksunT` | number | 통산착순상금 (원) | 18750000 |
| `rating` | number | 레이팅 | 0 |
| `hrLastAmt` | string | 최근거래가 | "30,000천원(경매)" |

#### ✅ 검증된 사용 사례
```javascript
// Node.js 예시 (JSON 사용 - 추천)
const response = await fetch(
  `https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey=${apiKey}&pageNo=1&numOfRows=10&hr_name=올라운드원&_type=json`
);
const jsonData = await response.json();

// 응답 데이터 처리
if (jsonData.response.body.items) {
  const horse = jsonData.response.body.items.item;
  console.log(`${horse.hrName} (${horse.hrNo})`);
  console.log(`통산 성적: ${horse.rcCntT}전 ${horse.ord1CntT}승`);
  console.log(`혈통: 부-${horse.faHrName}, 모-${horse.moHrName}`);
}
```

#### 📝 실제 응답 예시 (JSON)
```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE."
    },
    "body": {
      "items": {
        "item": {
          "birthday": 20220303,
          "chaksunT": 18750000,
          "faHrName": "사이먼퓨어",
          "faHrNo": "0031261",
          "hrLastAmt": "30,000천원(경매)",
          "hrName": "올라운드원",
          "hrNo": "0051228",
          "meet": "부산경남",
          "moHrName": "모닝퀸",
          "moHrNo": "0031853",
          "name": "한국",
          "ord1CntT": 1,
          "ord1CntY": 1,
          "ord2CntT": 0,
          "ord2CntY": 0,
          "ord3CntT": 0,
          "ord3CntY": 0,
          "owName": "김혜진",
          "owNo": 118011,
          "rank": "국5",
          "rating": 0,
          "rcCntT": 2,
          "rcCntY": 2,
          "sex": "거",
          "trName": "안우성",
          "trNo": "070180"
        }
      },
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

#### 🔍 주요 활용 포인트
1. **신마 분석**: 출주 기록이 적은 말의 혈통 정보 확인
2. **성적 추이**: 통산 vs 최근 1년 성적 비교로 현재 폼 판단
3. **거래가 정보**: 시장 가치 평가 참고
4. **등급 확인**: 현재 말의 경주 등급 파악

---

### 5. API19_1 - 조교사 상세정보

**API 이름**: 한국마사회 조교사 상세정보  
**Base URL**: `https://apis.data.go.kr/B551015/API19_1`  
**엔드포인트**: `/trainerInfo_1`
**HTTP 메서드**: GET

#### 📋 요청 파라미터
| 파라미터명 | 필수여부 | 타입 | 설명 | 예시 |
|-----------|---------|------|------|---------|
| ServiceKey | O | string | 서비스 인증키 | 발급받은 키 |
| pageNo | O | string | 페이지번호 | "1" |
| numOfRows | O | string | 한 페이지 결과 수 | "10" |
| meet | X | string | 시행경마장구분 (1:서울, 2:제주, 3:부산) | "1" |
| tr_name | X | string | 조교사명 | "안우성" |
| tr_no | X | string | 조교사번호 | "070180" |
| _type | X | string | 데이터형식변경 | "json" |

#### 🔗 요청 URL 예시
```
# JSON 응답 (추천)
https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey={KEY}&pageNo=1&numOfRows=10&tr_name=안우성&_type=json

# XML 응답 (기본값)
https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey={KEY}&pageNo=1&numOfRows=10&tr_name=안우성
```

#### 📊 응답 데이터 구조

**조교사 기본 정보 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|---------|
| `trName` | string | 조교사명 | "안우성" |
| `trNo` | string | 조교사번호 | "070180" |
| `age` | string | 나이 | "-" |
| `birthday` | string | 생년월일 | "-" |
| `meet` | string | 소속 경마장 | "부산경남" |
| `part` | number | 소속조 | 15 |
| `stDate` | number | 데뷔일자 (YYYYMMDD) | 20140601 |

**통산 성적 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|---------|
| `rcCntT` | number | 통산 출주횟수 | 2684 |
| `ord1CntT` | number | 통산 1착 횟수 | 323 |
| `ord2CntT` | number | 통산 2착 횟수 | 333 |
| `ord3CntT` | number | 통산 3착 횟수 | 308 |
| `winRateT` | number | 통산 승률 (%) | 12 |
| `plcRateT` | number | 통산 복승률 (%) | 35 |
| `qnlRateT` | number | 통산 연승률 (%) | 24 |

**최근 1년 성적 필드**:
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|---------|
| `rcCntY` | number | 최근1년 출주횟수 | 256 |
| `ord1CntY` | number | 최근1년 1착 횟수 | 16 |
| `ord2CntY` | number | 최근1년 2착 횟수 | 30 |
| `ord3CntY` | number | 최근1년 3착 횟수 | 38 |
| `winRateY` | number | 최근1년 승률 (%) | 6 |
| `plcRateY` | number | 최근1년 복승률 (%) | 32 |
| `qnlRateY` | number | 최근1년 연승률 (%) | 18 |

#### ✅ 검증된 사용 사례
```javascript
// Node.js 예시 (JSON 사용 - 추천)
const response = await fetch(
  `https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey=${apiKey}&pageNo=1&numOfRows=10&tr_name=안우성&_type=json`
);
const jsonData = await response.json();

// 응답 데이터 처리
if (jsonData.response.body.items) {
  const trainer = jsonData.response.body.items.item;
  console.log(`${trainer.trName} 조교사 (${trainer.meet})`);
  console.log(`통산: ${trainer.rcCntT}전 ${trainer.ord1CntT}승 (승률: ${trainer.winRateT}%)`);
  console.log(`최근1년: ${trainer.rcCntY}전 ${trainer.ord1CntY}승 (승률: ${trainer.winRateY}%)`);
}
```

#### 📝 실제 응답 예시 (JSON)
```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE."
    },
    "body": {
      "items": {
        "item": {
          "age": "-",
          "birthday": "-",
          "meet": "부산경남",
          "ord1CntT": 323,
          "ord1CntY": 16,
          "ord2CntT": 333,
          "ord2CntY": 30,
          "ord3CntT": 308,
          "ord3CntY": 38,
          "part": 15,
          "plcRateT": 35,
          "plcRateY": 32,
          "qnlRateT": 24,
          "qnlRateY": 18,
          "rcCntT": 2684,
          "rcCntY": 256,
          "stDate": 20140601,
          "trName": "안우성",
          "trNo": "070180",
          "winRateT": 12,
          "winRateY": 6
        }
      },
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

#### 🔍 주요 활용 포인트
1. **조교사 폼 분석**: 통산 vs 최근 1년 성적 비교
2. **복승률/연승률 활용**: 입상 가능성 평가
3. **데뷔 연차 계산**: stDate로 경력 파악
4. **경마장별 성적**: meet별로 조교사 성적 비교

---

## 🔧 API 활용 패턴

### 1. 경주 전 예측 분석
```javascript
// 1단계: API299로 통계 정보 수집
const statsResponse = await fetch(
  `https://apis.data.go.kr/B551015/API299/Race_Result_total?serviceKey=${key}&pageNo=1&numOfRows=20`
);

// 2단계: API12_1로 기수 정보 확인
const jockeyResponse = await fetch(
  `https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1?serviceKey=${key}&jk_name=김용근`
);

// 3단계: API8_2로 말 상세 정보 및 혈통 확인
const horseResponse = await fetch(
  `https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey=${key}&hr_name=올라운드원&_type=json`
);

// 4단계: API19_1로 조교사 상세 정보 확인
const trainerResponse = await fetch(
  `https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey=${key}&tr_name=안우성&_type=json`
);
```

### 2. 경주 후 결과 분석
```javascript
// API214_1로 상세 결과 조회
const raceResponse = await fetch(
  `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${key}&meet=1&rc_date=20250606&rc_no=1`
);
```

---

## 📋 데이터 처리 가이드

### 1. 응답 타입 설정 (XML vs JSON)

KRA API는 XML과 JSON 두 형식을 모두 지원합니다:

#### JSON 응답 요청 (추천)
```javascript
// _type=json 파라미터로 JSON 직접 수신
const url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${key}&numOfRows=50&pageNo=1&_type=json`;
const response = await fetch(url);
const jsonData = await response.json(); // 바로 JSON 사용 가능
```

#### XML 응답 처리 (기본값)
```javascript
// _type 파라미터 생략 시 XML 응답
import { parseStringPromise } from 'xml2js';

const xmlText = await response.text();
const jsonResult = await parseStringPromise(xmlText, {
  explicitArray: false,
  ignoreAttrs: true,
  trim: true,
});
```

#### 응답 타입 파라미터
| 파라미터 | 값 | 설명 | 예시 |
|-----------|-----|------|------|
| `_type` | `json` | JSON 형식 응답 | `&_type=json` |
| `_type` | `xml` | XML 형식 응답 (기본값) | `&_type=xml` |
| 생략 | - | XML 형식 응답 (기본값) | - |

### 2. 공통 응답 구조
```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <!-- 실제 데이터 -->
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>100</totalCount>
  </body>
</response>
```

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE."
    },
    "body": {
      "items": {
        "item": {
          "...": "실제 데이터"
        }
      },
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 100
    }
  }
}
```

### 4. 파라미터 인코딩 가이드
- 한글 및 특수문자를 포함한 파라미터는 `encodeURIComponent`로 인코딩하세요.
```javascript
const name = encodeURIComponent('김용근');
const url = `https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1?serviceKey=${key}&numOfRows=100&pageNo=1&jk_name=${name}&_type=json`;
```

### 5. cURL 호출 예시
```bash
# JSON 응답 예시 (한글 파라미터는 --data-urlencode 사용)
curl -G 'https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1' \
  --data-urlencode "serviceKey=$KRA_SERVICE_KEY" \
  --data-urlencode "numOfRows=100" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "jk_name=김용근" \
  --data-urlencode "_type=json"

# XML 응답 예시
curl -G 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1' \
  --data-urlencode "serviceKey=$KRA_SERVICE_KEY" \
  --data-urlencode "numOfRows=50" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "meet=1" \
  --data-urlencode "rc_date=20250606" \
  --data-urlencode "rc_no=1"
```

### 6. 데이터 타입 주의
- KRA JSON 응답은 숫자 필드가 문자열로 반환되는 경우가 있습니다. 파싱 시 숫자 변환을 고려하세요.
- 본 문서의 타입 표기는 “권장 사용 타입”으로 이해하시고, 실제 응답 타입은 샘플/실응답을 기준으로 처리하세요.

### 7. 페이지네이션 팁
- `pageNo`, `numOfRows`, `totalCount`를 활용하여 페이지 종료 조건을 판단하세요.
  - 예: `pageNo * numOfRows >= totalCount`이면 다음 페이지 요청 생략.
  - 또는 현재 페이지 `items`가 비어 있으면 종료.

### 3. 오류 처리
- `resultCode`: "00"이면 정상, 그 외는 오류
- `resultMsg`: 오류 메시지
- 주요 오류: `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`

---

## 🚨 주의사항 및 제한사항

### 1. API 호출 제한
- 공공데이터포털 정책에 따른 호출 제한 존재
- 과도한 호출 시 일시적 차단 가능

### 2. 데이터 가용성
- 과거 데이터는 제한적일 수 있음
- 실시간 데이터가 아님 (배치 처리)

### 3. 응답 형식
- 기본값은 XML
- `_type=json`으로 JSON 직접 수신 가능(권장)
- 본 문서의 예시는 JSON 사용 기준으로 작성되었습니다.

### 4. 경마장 코드
- 1: 서울
- 2: 제주  
- 3: 부산경남

---

## 📈 승률 및 예측 계산 공식

### 1. 말 승률 계산
```javascript
// 말의 통산 승률
const horseWinRate = (hrOrd1CntT / hrRcCntT) * 100;

// 말의 올해 승률
const horseWinRateThisYear = (hrOrd1CntY / hrRcCntY) * 100;

// 말의 연대율(1-3위)
const horsePlaceRate = ((hrOrd1CntT + hrOrd2CntT + hrOrd3CntT) / hrRcCntT) * 100;
```

### 2. 기수 승률 계산 (실제 API12_1 필드 사용)
```javascript
// 기수의 통산 승률 (API12_1 필드명)
const jockeyWinRate = (ord1CntT / rcCntT) * 100;

// 기수의 올해 승률
const jockeyWinRateThisYear = (ord1CntY / rcCntY) * 100;

// 기수의 연대율
const jockeyPlaceRate = ((ord1CntT + ord2CntT + ord3CntT) / rcCntT) * 100;

// 실제 데이터 예시 (김용근 기수)
const actualWinRate = (968 / 6254) * 100;        // 15.5%
const actualThisYearRate = (59 / 415) * 100;     // 14.2%
const actualPlaceRate = (2444 / 6254) * 100;     // 39.1%
```

### 3. 조교사 승률 계산
```javascript
// 조교사의 통산 승률
const trainerWinRate = (trOrd1CntT / trRcCntT) * 100;

// 조교사의 올해 승률
const trainerWinRateThisYear = (trOrd1CntY / trRcCntY) * 100;
```

### 4. 예측 지수 계산
```javascript
// 종합 예측 지수 (가중치 적용)
const predictionIndex = (
  (horseWinRate * 0.4) +          // 말 승률 40%
  (jockeyWinRate * 0.3) +         // 기수 승률 30%
  (trainerWinRate * 0.2) +        // 조교사 승률 20%
  (recentFormBonus * 0.1)         // 최근 폼 10%
);

// 최근 폼 보너스 계산
const recentFormBonus = jockeyWinRateThisYear > jockeyWinRate ? 10 : 0;
```

---

## 🔍 실제 사용 예시

### 완전한 Node.js 예시
```javascript
import fetch from 'node-fetch';
import { parseStringPromise } from 'xml2js';

async function getRaceData(apiKey, raceDate, raceNumber) {
  try {
    const url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${apiKey}&numOfRows=50&pageNo=1&meet=1&rc_date=${raceDate}&rc_no=${raceNumber}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const xmlText = await response.text();
    
    return await parseStringPromise(xmlText, {
      explicitArray: false,
      ignoreAttrs: true,
      trim: true,
    });
  } catch (error) {
    console.error('API 호출 실패:', error.message);
    throw error;
  }
}

// 사용법
const apiKey = process.env.KRA_SERVICE_KEY;
const raceData = await getRaceData(apiKey, '20250606', '1');
console.log(raceData.response.body.items.item);
```

---

## 📞 지원 및 문의

- **공공데이터포털**: https://data.go.kr
- **한국마사회**: https://kra.co.kr  
- **API 문의**: 공공데이터포털 고객센터

---

## 📈 데이터 활용 예시

### 경주 예측 시스템 구축
```javascript
class RacePredictionSystem {
  // 5개 API를 활용한 종합 예측 모델 구축
  async analyzePrediction(raceDate, raceNumber) {
    // 1단계: API299로 통계 데이터 수집
    const statsData = await this.getStatsData(raceDate, raceNumber);
    
    // 2단계: API214_1로 상세 경주 기록 수집
    const raceData = await this.getRaceData(raceDate, raceNumber);
    
    // 3단계: API12_1로 기수 정보 수집
    const jockeyData = await this.getJockeyData(jockeyName);
    
    // 4단계: API8_2로 말 상세 정보 및 혈통 수집
    const horseDetailData = await this.getHorseDetails(horseName);
    
    // 5단계: API19_1로 조교사 정보 수집
    const trainerData = await this.getTrainerDetails(trainerName);
    
    // 6단계: 종합 예측 지수 계산
    return this.calculatePredictionScore(statsData, raceData, jockeyData, horseDetailData, trainerData);
  }
  
  calculatePredictionScore(stats, race, jockey) {
    const horseScore = (stats.hrOrd1CntT / stats.hrRcCntT) * 40;
    const jockeyScore = (stats.jkOrd1CntT / stats.jkRcCntT) * 30;
    const trainerScore = (stats.trOrd1CntT / stats.trRcCntT) * 20;
    const recentFormScore = this.calculateRecentForm(stats) * 10;
    
    return horseScore + jockeyScore + trainerScore + recentFormScore;
  }
}
```

### 마권 투자 전략 시스템
```javascript
class BettingStrategy {
  // 배당률 가치 평가
  evaluateOddsValue(predictedWinRate, bookmakerOdds) {
    const impliedProbability = 1 / bookmakerOdds;
    const expectedValue = (predictedWinRate * bookmakerOdds) - 1;
    
    return {
      isValueBet: expectedValue > 0,
      expectedReturn: expectedValue,
      confidence: Math.abs(predictedWinRate - impliedProbability)
    };
  }
  
  // 위험 관리 및 베팅 금액 계산
  calculateBetSize(bankroll, winProbability, odds, riskTolerance = 0.05) {
    // 켈리 공식 적용
    const edge = (winProbability * odds) - 1;
    const kellyPercent = edge / (odds - 1);
    
    // 리스크 조정된 베팅 금액
    const adjustedPercent = Math.min(kellyPercent * riskTolerance, 0.1);
    return bankroll * adjustedPercent;
  }
}
```

---

## 📝 버전 정보

- **문서 버전**: 2.3
- **최종 업데이트**: 2025.09.06
- **검증된 API**: API214_1, API299, API12_1, API8_2, API19_1
- **변경 사항**: 응답 형식 안내 정정(JSON 권장 명시), 서비스키 표기/한글 인코딩 주의 추가, 각 API에 HTTP 메서드 표기, XML 파싱 예시(ESM) 업데이트, 공통 JSON 구조·cURL 예시·타입/페이지네이션 팁 추가
