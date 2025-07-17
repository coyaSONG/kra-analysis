# Node.js 데이터 수집 API

KRA 공공데이터 수집을 위한 간단한 Node.js API 서버입니다.

## 시작하기

```bash
# 의존성 설치
npm install

# 서버 실행
npm start

# 개발 모드 (nodemon 필요)
npm run dev
```

## API 엔드포인트

### 헬스체크
```
GET /health
```

### 데이터 수집
```
POST /collect
Body: {
  "date": "20241229",
  "meet": 1
}
```

### 데이터 보강
```
POST /enrich
Body: {
  "date": "20241229", 
  "meet": 1
}
```

### 경주 결과 조회
```
POST /result
Body: {
  "date": "20241229",
  "meet": 1,
  "raceNo": 1
}
```

## 아키텍처

```
Python FastAPI (포트 8000)
     ↓
Node.js API (포트 3001) 
     ↓
기존 Node.js 스크립트 실행
     ↓
KRA 공공데이터 API (HTTP)
```

## 특징

- 기존 Node.js 스크립트를 그대로 활용
- Python API와 느슨한 결합
- 간단한 HTTP 통신으로 연동
- SSL 문제 없음 (Node.js가 처리)