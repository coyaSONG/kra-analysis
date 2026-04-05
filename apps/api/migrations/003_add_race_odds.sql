-- Migration 003: Add race_odds table for high-volume odds data
-- Sources: API160_1 (확정배당율 통합), API301 (경마시행당일 확정배당율종합)

-- =============================================================================
-- race_odds table
-- =============================================================================
CREATE TABLE IF NOT EXISTS race_odds (
    id SERIAL PRIMARY KEY,
    race_id VARCHAR(50) NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
    pool VARCHAR(10) NOT NULL,
    chul_no INTEGER NOT NULL,               -- 1번마
    chul_no2 INTEGER NOT NULL DEFAULT 0,    -- 2번마 (연승식)
    chul_no3 INTEGER NOT NULL DEFAULT 0,    -- 3번마 (삼복승)
    odds DECIMAL(10,1) NOT NULL,
    rc_date VARCHAR(8) NOT NULL,
    source VARCHAR(20) NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 값 제약: 오탈자/대소문자로 UPSERT 무력화 방지
    CONSTRAINT chk_race_odds_pool CHECK (pool IN ('WIN', 'PLC', 'QNL', 'EXA', 'QPL', 'TLA', 'TRI', 'XLA')),
    CONSTRAINT chk_race_odds_source CHECK (source IN ('API160_1', 'API301')),

    -- 재수집 시 중복 방지: 같은 경주+승식+마번 조합+출처는 하나만 유지
    CONSTRAINT uq_race_odds_entry UNIQUE (race_id, pool, chul_no, chul_no2, chul_no3, source)
);

-- 경주별 배당률 조회 (가장 빈번한 패턴)
CREATE INDEX IF NOT EXISTS idx_race_odds_race_pool ON race_odds(race_id, pool);

-- 날짜별 배당률 조회 (시계열 분석, source 포함)
CREATE INDEX IF NOT EXISTS idx_race_odds_date_pool_source ON race_odds(rc_date, pool, source);

-- RLS (idempotent: DROP IF EXISTS before CREATE)
ALTER TABLE race_odds ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Service role full access" ON race_odds;
    CREATE POLICY "Service role full access" ON race_odds FOR ALL TO service_role USING (true) WITH CHECK (true);
    DROP POLICY IF EXISTS "Authenticated read access" ON race_odds;
    CREATE POLICY "Authenticated read access" ON race_odds FOR SELECT TO authenticated USING (true);
END $$;
