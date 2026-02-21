# Supabase 데이터베이스 설정 가이드

## 🎯 개요

이 가이드는 KRA API 서버를 Supabase 데이터베이스와 연결하는 전체 과정을 설명합니다.

## ⚠️ 현재 상태

- **연결 상태**: ❌ 미연결 (환경 변수 미설정)
- **마이그레이션**: ⚠️ 적용 필요
- **아키텍처**: 🟡 이중 시스템 (SQLAlchemy + Supabase Client)

## 📋 사전 준비

### 필요한 정보
- Supabase 프로젝트 URL: `https://[YOUR_SUPABASE_PROJECT_ID].supabase.co`
- Supabase 프로젝트 ID: `[YOUR_SUPABASE_PROJECT_ID]`
- Database 비밀번호 (Supabase Dashboard에서 확인/재설정)

### 시스템 요구사항
- Python 3.13+
- asyncpg
- SQLAlchemy 2.0+
- supabase-py

---

## 🚀 설정 단계

### 1단계: Supabase Dashboard에서 Credentials 확인

#### 1-1. 데이터베이스 비밀번호 확인/재설정

```bash
# 1. https://supabase.com/dashboard 로그인
# 2. kra-analysis 프로젝트 선택
# 3. Settings > Database
# 4. 비밀번호를 모르는 경우 "Reset database password" 클릭
# 5. 새 비밀번호를 안전한 곳에 저장
```

#### 1-2. Connection String 복사

Dashboard > Settings > Database에서:
- **"Connection string"** 섹션
- **"Pooler"** (Transaction mode) 선택
- Connection string 복사
- 형식: `postgresql://postgres.[YOUR_SUPABASE_PROJECT_ID]:[YOUR-PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`

#### 1-3. API Keys 확인

Dashboard > Settings > API에서:
- **"anon public"** 키 복사
- **"service_role"** 키 복사 (주의: 절대 클라이언트에 노출하지 말 것)

---

### 2단계: 환경 변수 설정

#### 2-1. .env 파일 생성

```bash
cd apps/api
cp .env.template .env
```

#### 2-2. .env 파일 편집

```bash
# 에디터로 .env 파일 열기
nano .env  # 또는 vim, code 등
```

#### 2-3. 값 입력

```env
# 환경
ENVIRONMENT=development

# 데이터베이스 (중요: 비밀번호 입력!)
DATABASE_URL=postgresql+asyncpg://postgres.[YOUR_SUPABASE_PROJECT_ID]:[실제-비밀번호]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0

# Supabase API
SUPABASE_URL=https://[YOUR_SUPABASE_PROJECT_ID].supabase.co
SUPABASE_ANON_KEY=[실제-anon-key]
SUPABASE_SERVICE_ROLE_KEY=[실제-service-role-key]

# KRA API
KRA_API_KEY=[실제-kra-api-key]

# 보안
SECRET_KEY=$(openssl rand -hex 32)
VALID_API_KEYS=["test-api-key-123456789"]
```

**특수 문자 URL 인코딩**:
비밀번호에 특수 문자가 있으면 URL 인코딩이 필요합니다:
```
! → %21    @ → %40    # → %23
$ → %24    % → %25    ^ → %5E
& → %26    * → %2A
```

예시:
```
비밀번호: myP@ss#123
인코딩: myP%40ss%23123
```

---

### 3단계: 연결 테스트

#### 3-1. 테스트 스크립트 실행

```bash
cd apps/api
python3 scripts/test_db_connection.py
```

#### 3-2. 예상 출력

```
================================================================================
Supabase 데이터베이스 연결 테스트
================================================================================

현재 설정 요약
================================================================================
환경: development
데이터베이스 URL: postgresql+asyncpg://postgres.[YOUR_SUPABASE_PROJECT_ID]:...
Supabase URL: https://[YOUR_SUPABASE_PROJECT_ID].supabase.co
Supabase Key: 설정됨
KRA API Key: 설정됨

================================================================================
1. asyncpg 직접 연결 테스트
================================================================================
연결 시도: postgresql://postgres.[YOUR_SUPABASE_PROJECT_ID]:...
✅ 연결 성공!
   PostgreSQL 버전: PostgreSQL 15.1 on x86_64-pc-linux-musl...
   현재 데이터베이스: postgres
   현재 사용자: postgres

================================================================================
2. SQLAlchemy 엔진 연결 테스트
================================================================================
엔진 생성 완료: aws-0-ap-northeast-2.pooler.supabase.com
✅ 연결 성공! 테스트 쿼리 결과: 1

================================================================================
3. 데이터베이스 테이블 확인
================================================================================
⚠️  테이블이 없습니다. 마이그레이션을 실행해야 합니다.

마이그레이션 실행:
   python3 scripts/apply_migrations.py

================================================================================
4. Supabase Python Client 테스트
================================================================================
✅ Supabase Client 초기화 성공!
   URL: https://[YOUR_SUPABASE_PROJECT_ID].supabase.co
```

#### 3-3. 문제 해결

**연결 실패 시**:
```bash
❌ 비밀번호 오류
→ Supabase Dashboard에서 비밀번호 재설정

❌ 연결 시간 초과
→ 네트워크 연결 확인
→ Supabase 프로젝트 상태 확인 (Dashboard에서)

❌ 인증 오류
→ 사용자 이름 확인: postgres.[YOUR_SUPABASE_PROJECT_ID]
→ Connection string 다시 복사
```

---

### 4단계: 데이터베이스 마이그레이션

#### 4-1. 마이그레이션 미리보기 (DRY RUN)

```bash
python3 scripts/apply_migrations.py --dry-run
```

#### 4-2. 마이그레이션 적용

```bash
python3 scripts/apply_migrations.py
```

**대화형 확인**:
```
마이그레이션을 적용하시겠습니까? (yes/no): yes
```

#### 4-3. 예상 출력

```
================================================================================
Supabase 마이그레이션 적용
================================================================================

발견된 마이그레이션 파일 3개:
   - 001_initial_schema.sql
   - 002_add_missing_columns.sql
   - 003_align_with_sqlalchemy_models.sql

데이터베이스 연결 중...
✅ 연결 성공

================================================================================
마이그레이션 상태 확인
================================================================================
ℹ️  테이블이 없습니다. 새로운 데이터베이스입니다.

적용 중: 003_align_with_sqlalchemy_models.sql
--------------------------------------------------------------------------------
SQL 미리보기:
  DO $$
  BEGIN
  ...
✅ 003_align_with_sqlalchemy_models.sql 적용 완료

================================================================================
스키마 검증
================================================================================

필수 테이블 확인:
   ✅ races
   ✅ race_results
   ✅ predictions
   ✅ collection_jobs
   ✅ horse_cache
   ✅ jockey_cache
   ✅ trainer_cache
   ✅ prompt_versions
   ✅ performance_analysis

Row Level Security 정책:
   ✅ races: Enable all for authenticated users
   ✅ race_results: Enable all for authenticated users
   ...

================================================================================
결과 요약
================================================================================
총 마이그레이션: 3개
성공: 3개
실패/스킵: 0개

🎉 모든 마이그레이션이 성공적으로 적용되었습니다!
```

#### 4-4. 주의사항

⚠️ **003_align_with_sqlalchemy_models.sql**는 기존 테이블을 삭제합니다!
- 데이터가 있는 프로덕션 환경에서는 **주의**
- 백업 권장: 마이그레이션 파일 내 주석 처리된 백업 코드 활성화

---

### 5단계: API 서버 시작

#### 5-1. 서버 실행

```bash
cd apps/api
python3 main_v2.py
```

#### 5-2. 예상 로그

```json
{"event": "Starting KRA Unified API Server", "version": "2.0.0", "environment": "development"}
{"event": "Directory created or verified: ./data"}
{"event": "Database initialized successfully"}
{"event": "Redis initialized successfully"}
```

#### 5-3. Health Check

```bash
# 간단한 헬스체크
curl http://localhost:8000/health

# 상세 헬스체크
curl http://localhost:8000/health/detailed
```

**예상 응답**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "celery": "unknown",
  "timestamp": 1727721234.567,
  "version": "2.0.0"
}
```

---

## 🔍 검증 단계

### 데이터 삽입 테스트

```bash
curl -X POST http://localhost:8000/api/v2/collection/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-123456789" \
  -d '{
    "date": "20240719",
    "meet": 1,
    "race_numbers": [1]
  }'
```

### Supabase Dashboard에서 확인

1. Dashboard > Table Editor
2. `races` 테이블 선택
3. 데이터 확인

---

## 🏗️ 아키텍처 이해

### 현재 이중 시스템

```
┌─────────────────────────────────────────────────┐
│                 API 서버                         │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────┐    ┌──────────────────┐  │
│  │  Legacy System   │    │  Modern System   │  │
│  │  (race.py)       │    │  (collection_v2) │  │
│  │                  │    │                  │  │
│  │  RaceService     │    │  CollectionSvc   │  │
│  └────────┬─────────┘    └────────┬─────────┘  │
│           │                       │             │
│           │                       │             │
│  ┌────────▼─────────┐    ┌────────▼─────────┐  │
│  │ Supabase Client  │    │   SQLAlchemy     │  │
│  │  (supabase-py)   │    │   + asyncpg      │  │
│  └────────┬─────────┘    └────────┬─────────┘  │
│           │                       │             │
└───────────┼───────────────────────┼─────────────┘
            │                       │
            └───────────┬───────────┘
                        │
            ┌───────────▼──────────┐
            │  Supabase PostgreSQL │
            │  [YOUR_SUPABASE_PROJECT_ID]│
            └──────────────────────┘
```

### 권장 사항

**단기**: 두 시스템 유지 (현재)
- Legacy 코드는 in-memory fallback 사용
- Modern 코드는 SQLAlchemy로 DB 접근

**중기**: SQLAlchemy로 통일
- `race_service.py` 리팩토링
- Supabase Client 제거 또는 Read-only로 제한

**장기**: Supabase 기능 활용
- Row Level Security (RLS)
- Realtime 구독
- Edge Functions
- Storage

---

## 📊 모니터링

### Supabase Dashboard

- **Logs**: Dashboard > Logs
  - Postgres logs
  - API logs
- **Performance**: Dashboard > Reports
  - Query performance
  - Connection pool 상태

### 로컬 로그

```bash
# API 로그
tail -f logs/api.log

# 구조화된 로그 (JSON)
tail -f logs/api.log | jq .
```

---

## 🚨 문제 해결

### 연결 문제

**증상**: `Connection terminated due to connection timeout`

**원인**:
1. 비밀번호 오류
2. 네트워크 문제
3. Supabase 프로젝트 일시 중지

**해결**:
```bash
# 1. 비밀번호 확인
cat .env | grep DATABASE_URL

# 2. 프로젝트 상태 확인 (Dashboard)
# https://supabase.com/dashboard/project/[YOUR_SUPABASE_PROJECT_ID]

# 3. 연결 테스트
python3 scripts/test_db_connection.py
```

### 마이그레이션 실패

**증상**: `DuplicateTableError`

**원인**: 테이블이 이미 존재

**해결**:
```bash
# Option 1: 테이블 삭제 (데이터 유실!)
# Supabase Dashboard > SQL Editor
DROP TABLE IF EXISTS races CASCADE;
DROP TABLE IF EXISTS race_results CASCADE;
# ...

# Option 2: 마이그레이션 파일 수정
# IF NOT EXISTS 조건 확인
```

### 스키마 불일치

**증상**: SQLAlchemy 오류 (`column does not exist`)

**원인**: 모델과 실제 테이블 불일치

**해결**:
```bash
# 1. 현재 스키마 확인
psql "$DATABASE_URL" -c "\d races"

# 2. 003 마이그레이션 재적용
python3 scripts/apply_migrations.py
```

---

## 🔐 보안 체크리스트

```markdown
[ ] .env 파일은 .gitignore에 포함됨
[ ] 비밀번호는 안전한 곳에 저장
[ ] SERVICE_ROLE_KEY는 서버에서만 사용
[ ] 프로덕션에서는 ENVIRONMENT=production 설정
[ ] 프로덕션 SECRET_KEY는 랜덤 생성: openssl rand -hex 32
[ ] RLS (Row Level Security) 정책 검토
[ ] API Keys 정기 교체
```

---

## 📚 추가 참고자료

- [Supabase 공식 문서](https://supabase.com/docs)
- [asyncpg 문서](https://magicstack.github.io/asyncpg/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [pgbouncer FAQ](https://www.pgbouncer.org/faq.html)

---

## 🎯 다음 단계

1. ✅ 데이터베이스 연결 완료
2. ✅ 마이그레이션 적용 완료
3. 🔄 실제 데이터 수집 테스트
4. 🔄 Legacy 시스템 마이그레이션 계획
5. 🔄 프로덕션 배포 준비