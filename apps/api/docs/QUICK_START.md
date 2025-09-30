# 빠른 시작 가이드

## 📋 체크리스트

```bash
# 1. 환경 변수 설정
[ ] .env 파일 생성됨
[ ] DATABASE_URL 설정됨 (Supabase)
[ ] SUPABASE_URL 설정됨
[ ] SUPABASE_ANON_KEY 설정됨
[ ] KRA_API_KEY 설정됨

# 2. 연결 테스트
[ ] python3 scripts/test_db_connection.py 성공

# 3. 마이그레이션
[ ] python3 scripts/apply_migrations.py 완료

# 4. 서버 시작
[ ] python3 main_v2.py 성공
[ ] curl http://localhost:8000/health 성공
```

## 🚀 5분 설정

### 1. 환경 파일 생성

```bash
cd apps/api
cp .env.template .env
```

### 2. Supabase Credentials 입력

`.env` 파일 편집:
```env
DATABASE_URL=postgresql+asyncpg://postgres.kwhwqhopxxhcpbcmfdxh:[비밀번호]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
SUPABASE_URL=https://kwhwqhopxxhcpbcmfdxh.supabase.co
SUPABASE_ANON_KEY=[your-anon-key]
KRA_API_KEY=[your-kra-api-key]
```

**비밀번호 & API Keys 찾기**:
1. https://supabase.com/dashboard 로그인
2. kra-analysis 프로젝트 선택
3. **Database 비밀번호**: Settings > Database > "Reset database password"
4. **API Keys**: Settings > API
   - "Project API keys" 섹션에서
   - `anon` / `public` 키 복사 → SUPABASE_ANON_KEY
   - `service_role` 키 복사 → SUPABASE_SERVICE_ROLE_KEY
   - (JWT 형식: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

### 3. 연결 테스트

```bash
python3 scripts/test_db_connection.py
```

**예상 결과**: 모든 테스트 ✅

### 4. 마이그레이션 적용

```bash
# 미리보기
python3 scripts/apply_migrations.py --dry-run

# 적용
python3 scripts/apply_migrations.py
```

입력 프롬프트에서 `yes` 입력

### 5. 서버 시작

```bash
python3 main_v2.py
```

### 6. 동작 확인

```bash
# Health check
curl http://localhost:8000/health/detailed

# API 문서
open http://localhost:8000/docs
```

## ❌ 문제 해결

### "Connection timeout"

```bash
# 비밀번호 확인
cat .env | grep DATABASE_URL

# Supabase 프로젝트 상태 확인
# https://supabase.com/dashboard/project/kwhwqhopxxhcpbcmfdxh
```

### "Password authentication failed"

```bash
# Supabase Dashboard에서 비밀번호 재설정
# Settings > Database > Reset database password
```

### Pydantic 경고

이미 수정됨 (config.py에서 `Config` → `model_config`)

## 📚 자세한 문서

- [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) - 전체 설정 가이드
- [database-connection-issue.md](./database-connection-issue.md) - 연결 문제 해결

## 🎯 다음 단계

1. 데이터 수집 테스트:
```bash
curl -X POST http://localhost:8000/api/v2/collection/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-123456789" \
  -d '{"date": "20240719", "meet": 1, "race_numbers": [1]}'
```

2. Supabase Dashboard에서 데이터 확인

3. 테스트 실행:
```bash
pytest tests/ -v
```