# Database Connection Issue - Resolution Guide

## Problem Summary
The API server cannot connect to the Supabase PostgreSQL database due to authentication failure.

## Root Cause
**Wrong password**: The password `yeon07042408*` stored in the `.env` file is incorrect for the Supabase project.

## Diagnosis Steps Taken

### 1. Project ID Verification
- ✅ Fixed incorrect project ID: `bsyxzpxiukmxjzwkgitg` → `kwhwqhopxxhcpbcmfdxh`
- ✅ Project status: ACTIVE_HEALTHY
- ✅ Database host: `db.kwhwqhopxxhcpbcmfdxh.supabase.co`

### 2. Connection Testing Results
- ❌ asyncpg: "unexpected error while performing authentication: 'NoneType' object has no attribute 'group'"
- ❌ psycopg2: "Wrong password"
- ✅ MCP Supabase: Works (uses different authentication method)

### 3. Error Analysis
The asyncpg error is misleading - it's actually a password authentication failure that manifests as a SCRAM authentication error in asyncpg.

## Resolution Steps

### Option 1: Get Correct Password from Supabase Dashboard
1. Log in to [Supabase Dashboard](https://supabase.com/dashboard)
2. Navigate to your project: `kra-analysis`
3. Go to Settings → Database
4. Copy the database password
5. Update `.env` file with the correct password

### Option 2: Reset Database Password
1. In Supabase Dashboard, go to Settings → Database
2. Click "Reset database password"
3. Copy the new password
4. Update `.env` file

### Option 3: Use Connection String from Dashboard
1. In Supabase Dashboard, go to Settings → Database
2. Find "Connection string" section
3. Copy the "Pooler" connection string (for pgbouncer)
4. Replace the connection string in `.env`

## Correct .env Configuration

```bash
# 데이터베이스 설정
DATABASE_URL=postgresql+asyncpg://postgres.kwhwqhopxxhcpbcmfdxh:[CORRECT_PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

## Important Notes

1. **Password Encoding**: Special characters in the password must be URL-encoded:
   - `*` → `%2A`
   - `@` → `%40`
   - `#` → `%23`

2. **Connection Types**:
   - **Pooler (Recommended)**: Port 6543, user `postgres.{project_id}`
   - **Direct**: Port 5432, user `postgres`
   - **Transaction Mode**: Port 5432, user `postgres.{project_id}`

3. **pgbouncer Compatibility**:
   - Always include `?prepared_statement_cache_size=0` in the connection string
   - The code already handles this in `infrastructure/database.py`

## Verification

After updating the password, test the connection:

```bash
# Test database connection
python3 scripts/test_db_connection.py

# Run the server
python3 main_v2.py
```

## Security Reminder

- Never commit passwords to version control
- Use environment variables for sensitive data
- Consider using a `.env.example` file with placeholder values