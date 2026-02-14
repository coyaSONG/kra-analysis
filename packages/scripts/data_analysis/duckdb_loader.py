#!/usr/bin/env python3
"""
DuckDB 기반 경마 데이터 분석 모듈

enriched JSON 파일과 결과 파일을 DuckDB로 로드하여
SQL 기반 분석을 수행합니다. analyze_enriched_patterns.py의
수동 집계를 대체하는 강력한 분석 도구입니다.

사용법:
    # 전체 분석 실행
    python3 data_analysis/duckdb_loader.py

    # 특정 분석만 실행
    python3 data_analysis/duckdb_loader.py --analysis odds
    python3 data_analysis/duckdb_loader.py --analysis jockey
    python3 data_analysis/duckdb_loader.py --analysis horse
    python3 data_analysis/duckdb_loader.py --analysis venue

    # 커스텀 SQL 쿼리
    python3 data_analysis/duckdb_loader.py --query "SELECT COUNT(*) FROM horses"
"""

import argparse
import glob
import json
from pathlib import Path

import duckdb


class RaceDataAnalyzer:
    """DuckDB 기반 경마 데이터 분석기"""

    # 경마장 코드 매핑 (디렉토리명 -> 결과 파일 경마장명)
    VENUE_MAP = {"seoul": "서울", "busan": "부산경남", "jeju": "제주"}
    # 역매핑 (결과 파일 경마장명 -> 디렉토리명)
    VENUE_REVERSE_MAP = {v: k for k, v in VENUE_MAP.items()}

    def __init__(self, data_dir: str = "data"):
        """DuckDB 연결을 초기화하고 데이터를 로드합니다.

        Args:
            data_dir: 데이터 루트 디렉토리 경로
        """
        self.conn = duckdb.connect()  # in-memory
        self.data_dir = Path(data_dir)
        self._horses_loaded = 0
        self._results_loaded = 0
        self._load_data()

    def _load_data(self):
        """enriched JSON 파일과 결과 파일을 DuckDB 테이블로 로드합니다."""
        self._create_tables()
        self._load_enriched_files()
        self._load_result_files()
        self._print_load_summary()

    def _create_tables(self):
        """분석용 테이블 스키마를 생성합니다."""
        self.conn.execute("""
            CREATE TABLE horses (
                -- 경주 메타데이터
                race_date VARCHAR,
                meet VARCHAR,
                race_no INTEGER,
                venue VARCHAR,

                -- 말 기본 정보
                chul_no INTEGER,
                hr_name VARCHAR,
                hr_no VARCHAR,
                jk_name VARCHAR,
                jk_no VARCHAR,
                tr_name VARCHAR,
                tr_no VARCHAR,
                win_odds DOUBLE,
                budam DOUBLE,
                buga1 DOUBLE,

                -- 말 상세정보 (hrDetail)
                hr_rc_cnt_t INTEGER,
                hr_ord1_cnt_t INTEGER,
                hr_ord2_cnt_t INTEGER,
                hr_ord3_cnt_t INTEGER,
                hr_rc_cnt_y INTEGER,
                hr_ord1_cnt_y INTEGER,
                hr_win_rate_t DOUBLE,
                hr_plc_rate_t DOUBLE,
                hr_win_rate_y DOUBLE,
                hr_rating DOUBLE,

                -- 기수 상세정보 (jkDetail)
                jk_rc_cnt_t INTEGER,
                jk_ord1_cnt_t INTEGER,
                jk_ord2_cnt_t INTEGER,
                jk_ord3_cnt_t INTEGER,
                jk_win_rate_t DOUBLE,
                jk_plc_rate_t DOUBLE,
                jk_win_rate_y DOUBLE,

                -- 조교사 상세정보 (trDetail)
                tr_rc_cnt_t INTEGER,
                tr_ord1_cnt_t INTEGER,
                tr_win_rate_t DOUBLE,
                tr_plc_rate_t DOUBLE,
                tr_win_rate_y DOUBLE,

                -- 상세정보 존재 여부
                has_hr_detail BOOLEAN,
                has_jk_detail BOOLEAN,
                has_tr_detail BOOLEAN
            )
        """)

        self.conn.execute("""
            CREATE TABLE results (
                race_date VARCHAR,
                meet VARCHAR,
                race_no INTEGER,
                rank INTEGER,
                chul_no INTEGER
            )
        """)

    def _safe_float(self, value, default=0.0) -> float:
        """안전하게 float 변환합니다."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _safe_int(self, value, default=0) -> int:
        """안전하게 int 변환합니다."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _load_enriched_files(self):
        """enriched JSON 파일들을 horses 테이블로 로드합니다."""
        pattern = str(
            self.data_dir / "races" / "*" / "*" / "*" / "*" / "*_enriched.json"
        )
        files = sorted(glob.glob(pattern))

        if not files:
            print(f"[INFO] enriched 파일을 찾을 수 없습니다: {pattern}")
            return

        rows = []
        skipped = 0

        for filepath in files:
            try:
                # 파일명에서 메타데이터 추출
                # 패턴: race_{meet}_{date}_{raceNo}_enriched.json
                path_obj = Path(filepath)
                filename = path_obj.name
                venue = path_obj.parent.name  # seoul, busan, jeju

                parts = filename.replace("_enriched.json", "").split("_")
                if len(parts) < 4:
                    skipped += 1
                    continue

                meet = parts[1]  # meet code (1, 2, 3)
                race_date = parts[2]  # YYYYMMDD
                race_no = int(parts[3])

                # JSON 로드
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                # 말 데이터 추출
                items = (
                    data.get("response", {})
                    .get("body", {})
                    .get("items", {})
                    .get("item", [])
                )
                if not isinstance(items, list):
                    items = [items]

                for horse in items:
                    win_odds = self._safe_float(horse.get("winOdds"))
                    if win_odds <= 0:
                        continue  # 기권/제외마 필터링

                    hr_detail = horse.get("hrDetail") or {}
                    jk_detail = horse.get("jkDetail") or {}
                    tr_detail = horse.get("trDetail") or {}

                    row = (
                        # 경주 메타데이터
                        race_date,
                        meet,
                        race_no,
                        venue,
                        # 말 기본 정보
                        self._safe_int(horse.get("chulNo")),
                        horse.get("hrName", ""),
                        str(horse.get("hrNo", "")),
                        horse.get("jkName", ""),
                        str(horse.get("jkNo", "")),
                        horse.get("trName", ""),
                        str(horse.get("trNo", "")),
                        win_odds,
                        self._safe_float(horse.get("budam")),
                        self._safe_float(horse.get("buga1")),
                        # 말 상세정보
                        self._safe_int(hr_detail.get("rcCntT")),
                        self._safe_int(hr_detail.get("ord1CntT")),
                        self._safe_int(hr_detail.get("ord2CntT")),
                        self._safe_int(hr_detail.get("ord3CntT")),
                        self._safe_int(hr_detail.get("rcCntY")),
                        self._safe_int(hr_detail.get("ord1CntY")),
                        self._safe_float(hr_detail.get("winRateT")),
                        self._safe_float(hr_detail.get("plcRateT")),
                        self._safe_float(hr_detail.get("winRateY")),
                        self._safe_float(hr_detail.get("rating")),
                        # 기수 상세정보
                        self._safe_int(jk_detail.get("rcCntT")),
                        self._safe_int(jk_detail.get("ord1CntT")),
                        self._safe_int(jk_detail.get("ord2CntT")),
                        self._safe_int(jk_detail.get("ord3CntT")),
                        self._safe_float(jk_detail.get("winRateT")),
                        self._safe_float(jk_detail.get("plcRateT")),
                        self._safe_float(jk_detail.get("winRateY")),
                        # 조교사 상세정보
                        self._safe_int(tr_detail.get("rcCntT")),
                        self._safe_int(tr_detail.get("ord1CntT")),
                        self._safe_float(tr_detail.get("winRateT")),
                        self._safe_float(tr_detail.get("plcRateT")),
                        self._safe_float(tr_detail.get("winRateY")),
                        # 상세정보 존재 여부
                        bool(horse.get("hrDetail")),
                        bool(horse.get("jkDetail")),
                        bool(horse.get("trDetail")),
                    )
                    rows.append(row)

            except Exception as e:
                print(f"[WARN] 파일 로드 실패 ({filepath}): {e}")
                skipped += 1

        if rows:
            self.conn.executemany(
                "INSERT INTO horses VALUES (" + ", ".join(["?"] * 36) + ")",
                rows,
            )
            self._horses_loaded = len(rows)

        if skipped > 0:
            print(f"[WARN] {skipped}개 파일 건너뜀")

    def _load_result_files(self):
        """결과 JSON 파일들을 results 테이블로 로드합니다."""
        pattern = str(self.data_dir / "cache" / "results" / "top3_*.json")
        files = sorted(glob.glob(pattern))

        if not files:
            print(f"[INFO] 결과 파일을 찾을 수 없습니다: {pattern}")
            return

        rows = []
        skipped = 0

        for filepath in files:
            try:
                # 파일명에서 메타데이터 추출
                # 패턴: top3_{date}_{meet}_{raceNo}.json
                filename = Path(filepath).stem  # top3_20250601_서울_1
                parts = filename.split("_")

                if len(parts) < 4:
                    skipped += 1
                    continue

                race_date = parts[1]  # YYYYMMDD
                meet_name = parts[2]  # 서울, 부산경남, 제주
                race_no = int(parts[3])

                # meet_name을 meet 코드로 변환
                meet_code_map = {"서울": "1", "제주": "2", "부산경남": "3"}
                meet = meet_code_map.get(meet_name, meet_name)

                # JSON 로드
                with open(filepath, encoding="utf-8") as f:
                    top3 = json.load(f)

                if not isinstance(top3, list) or len(top3) != 3:
                    skipped += 1
                    continue

                for rank_idx, chul_no in enumerate(top3):
                    rows.append(
                        (
                            race_date,
                            meet,
                            race_no,
                            rank_idx + 1,  # 1위, 2위, 3위
                            int(chul_no),
                        )
                    )

            except Exception as e:
                print(f"[WARN] 결과 파일 로드 실패 ({filepath}): {e}")
                skipped += 1

        if rows:
            self.conn.executemany(
                "INSERT INTO results VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            self._results_loaded = len(rows) // 3  # 경주 수 기준

        if skipped > 0:
            print(f"[WARN] 결과 파일 {skipped}개 건너뜀")

    def _print_load_summary(self):
        """데이터 로드 요약을 출력합니다."""
        print(f"\n{'=' * 60}")
        print("DuckDB 데이터 로드 완료")
        print(f"{'=' * 60}")
        print(f"  horses 테이블: {self._horses_loaded:,}행 (유효 출전마)")
        print(f"  results 테이블: {self._results_loaded:,}개 경주")

        # 매칭된 경주 수 확인
        if self._horses_loaded > 0 and self._results_loaded > 0:
            matched = self.conn.execute("""
                SELECT COUNT(DISTINCT (h.race_date || '_' || h.meet || '_' || h.race_no))
                FROM horses h
                INNER JOIN results r
                    ON h.race_date = r.race_date
                    AND h.meet = r.meet
                    AND h.race_no = r.race_no
            """).fetchone()[0]
            print(f"  매칭된 경주: {matched:,}개 (horses + results 모두 존재)")
        print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # 분석 메서드
    # ------------------------------------------------------------------

    def odds_rank_analysis(self) -> str:
        """배당률 순위별 실제 입상률(top-3) 분석

        각 경주에서 배당률이 낮은 순서대로 순위를 매기고,
        해당 순위의 말이 실제로 1-3위에 들었는지 분석합니다.
        """
        sql = """
        WITH odds_ranked AS (
            SELECT
                h.*,
                ROW_NUMBER() OVER (
                    PARTITION BY h.race_date, h.meet, h.race_no
                    ORDER BY h.win_odds ASC
                ) AS odds_rank
            FROM horses h
        ),
        with_result AS (
            SELECT
                o.odds_rank,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM odds_ranked o
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON o.race_date = races.race_date
                AND o.meet = races.meet
                AND o.race_no = races.race_no
            LEFT JOIN results r
                ON o.race_date = r.race_date
                AND o.meet = r.meet
                AND o.race_no = r.race_no
                AND o.chul_no = r.chul_no
        )
        SELECT
            odds_rank AS "순위",
            COUNT(*) AS "출전",
            SUM(is_top3) AS "입상",
            ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1) AS "입상률(%)",
            ROUND(
                SUM(SUM(is_top3)) OVER (ORDER BY odds_rank)
                * 100.0
                / SUM(COUNT(*)) OVER (ORDER BY odds_rank),
                1
            ) AS "누적입상률(%)"
        FROM with_result
        WHERE odds_rank <= 15
        GROUP BY odds_rank
        ORDER BY odds_rank
        """

        print("\n[배당률 순위별 실제 입상률]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)

        # 핵심 인사이트: 상위 3위 배당률 말의 입상률
        insight_sql = """
        WITH odds_ranked AS (
            SELECT
                h.*,
                ROW_NUMBER() OVER (
                    PARTITION BY h.race_date, h.meet, h.race_no
                    ORDER BY h.win_odds ASC
                ) AS odds_rank
            FROM horses h
        ),
        with_result AS (
            SELECT
                o.odds_rank,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM odds_ranked o
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON o.race_date = races.race_date
                AND o.meet = races.meet
                AND o.race_no = races.race_no
            LEFT JOIN results r
                ON o.race_date = r.race_date
                AND o.meet = r.meet
                AND o.race_no = r.race_no
                AND o.chul_no = r.chul_no
        )
        SELECT
            ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1) AS rate
        FROM with_result
        WHERE odds_rank <= 3
        """
        row = self.conn.execute(insight_sql).fetchone()
        if row and row[0] is not None:
            print(f"\n  >> 배당률 1-3위 말의 평균 입상률: {row[0]}%")

        return result

    def jockey_performance(self) -> str:
        """기수 승률 구간별 실제 입상률 분석

        기수의 통산 승률을 5% 구간으로 나누고,
        해당 구간 기수가 탄 말의 실제 입상률을 계산합니다.
        """
        sql = """
        WITH jockey_binned AS (
            SELECT
                h.chul_no,
                h.race_date,
                h.meet,
                h.race_no,
                h.jk_name,
                h.jk_rc_cnt_t,
                h.jk_ord1_cnt_t,
                CASE
                    WHEN h.jk_rc_cnt_t > 0
                    THEN CAST(FLOOR(h.jk_ord1_cnt_t * 100.0 / h.jk_rc_cnt_t / 5) * 5 AS INTEGER)
                    ELSE -1
                END AS win_rate_bin
            FROM horses h
            WHERE h.has_jk_detail = true
              AND h.jk_rc_cnt_t > 0
        ),
        with_result AS (
            SELECT
                jb.win_rate_bin,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM jockey_binned jb
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON jb.race_date = races.race_date
                AND jb.meet = races.meet
                AND jb.race_no = races.race_no
            LEFT JOIN results r
                ON jb.race_date = r.race_date
                AND jb.meet = r.meet
                AND jb.race_no = r.race_no
                AND jb.chul_no = r.chul_no
        )
        SELECT
            CONCAT(win_rate_bin, '-', win_rate_bin + 5, '%') AS "승률대",
            COUNT(*) AS "출전",
            SUM(is_top3) AS "입상",
            ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1) AS "입상률(%)"
        FROM with_result
        WHERE win_rate_bin >= 0
        GROUP BY win_rate_bin
        ORDER BY win_rate_bin
        """

        print("\n[기수 승률 구간별 실제 입상률]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)

        # 핵심 인사이트: 승률 15% 이상 기수의 입상률
        insight_sql = """
        WITH jockey_data AS (
            SELECT
                h.chul_no, h.race_date, h.meet, h.race_no,
                h.jk_ord1_cnt_t * 100.0 / h.jk_rc_cnt_t AS win_rate
            FROM horses h
            WHERE h.has_jk_detail = true AND h.jk_rc_cnt_t > 0
        ),
        with_result AS (
            SELECT
                jd.win_rate,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM jockey_data jd
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON jd.race_date = races.race_date
                AND jd.meet = races.meet
                AND jd.race_no = races.race_no
            LEFT JOIN results r
                ON jd.race_date = r.race_date
                AND jd.meet = r.meet
                AND jd.race_no = r.race_no
                AND jd.chul_no = r.chul_no
        )
        SELECT ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1)
        FROM with_result
        WHERE win_rate >= 15
        """
        row = self.conn.execute(insight_sql).fetchone()
        if row and row[0] is not None:
            print(f"\n  >> 기수 승률 15% 이상 말의 입상률: {row[0]}%")

        return result

    def horse_performance(self) -> str:
        """말 과거 입상률 구간별 실제 입상률 분석

        말의 통산 입상률(1+2+3착/출전)을 10% 구간으로 나누고,
        해당 구간 말의 실제 입상률을 계산합니다.
        """
        sql = """
        WITH horse_binned AS (
            SELECT
                h.chul_no,
                h.race_date,
                h.meet,
                h.race_no,
                h.hr_name,
                h.hr_rc_cnt_t,
                (h.hr_ord1_cnt_t + h.hr_ord2_cnt_t + h.hr_ord3_cnt_t) AS place_cnt,
                CASE
                    WHEN h.hr_rc_cnt_t > 0
                    THEN CAST(
                        FLOOR(
                            (h.hr_ord1_cnt_t + h.hr_ord2_cnt_t + h.hr_ord3_cnt_t)
                            * 100.0 / h.hr_rc_cnt_t / 10
                        ) * 10
                        AS INTEGER
                    )
                    ELSE -1
                END AS place_rate_bin
            FROM horses h
            WHERE h.has_hr_detail = true
              AND h.hr_rc_cnt_t > 0
        ),
        with_result AS (
            SELECT
                hb.place_rate_bin,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM horse_binned hb
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON hb.race_date = races.race_date
                AND hb.meet = races.meet
                AND hb.race_no = races.race_no
            LEFT JOIN results r
                ON hb.race_date = r.race_date
                AND hb.meet = r.meet
                AND hb.race_no = r.race_no
                AND hb.chul_no = r.chul_no
        )
        SELECT
            CONCAT(place_rate_bin, '-', place_rate_bin + 10, '%') AS "입상률대",
            COUNT(*) AS "출전",
            SUM(is_top3) AS "입상",
            ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1) AS "입상률(%)"
        FROM with_result
        WHERE place_rate_bin >= 0
        GROUP BY place_rate_bin
        ORDER BY place_rate_bin
        """

        print("\n[말 과거 입상률 구간별 실제 입상률]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)

        # 핵심 인사이트: 입상률 30% 이상 말의 입상률
        insight_sql = """
        WITH horse_data AS (
            SELECT
                h.chul_no, h.race_date, h.meet, h.race_no,
                (h.hr_ord1_cnt_t + h.hr_ord2_cnt_t + h.hr_ord3_cnt_t)
                    * 100.0 / h.hr_rc_cnt_t AS place_rate
            FROM horses h
            WHERE h.has_hr_detail = true AND h.hr_rc_cnt_t > 0
        ),
        with_result AS (
            SELECT
                hd.place_rate,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM horse_data hd
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON hd.race_date = races.race_date
                AND hd.meet = races.meet
                AND hd.race_no = races.race_no
            LEFT JOIN results r
                ON hd.race_date = r.race_date
                AND hd.meet = r.meet
                AND hd.race_no = r.race_no
                AND hd.chul_no = r.chul_no
        )
        SELECT ROUND(SUM(is_top3) * 100.0 / COUNT(*), 1)
        FROM with_result
        WHERE place_rate >= 30
        """
        row = self.conn.execute(insight_sql).fetchone()
        if row and row[0] is not None:
            print(f"\n  >> 말 과거 입상률 30% 이상의 실제 입상률: {row[0]}%")

        return result

    def top_jockeys(self, min_races: int = 10) -> str:
        """최소 출전 횟수 이상의 기수를 승률 기준 상위로 출력합니다.

        Args:
            min_races: 최소 출전 횟수
        """
        sql = f"""
        WITH jockey_stats AS (
            SELECT
                h.jk_name,
                h.jk_no,
                MAX(h.jk_rc_cnt_t) AS total_races,
                MAX(h.jk_ord1_cnt_t) AS wins,
                MAX(h.jk_ord1_cnt_t + h.jk_ord2_cnt_t + h.jk_ord3_cnt_t) AS places,
                ROUND(MAX(h.jk_win_rate_t), 1) AS win_rate,
                ROUND(MAX(h.jk_plc_rate_t), 1) AS place_rate,
                COUNT(DISTINCT (h.race_date || '_' || h.race_no)) AS races_in_data
            FROM horses h
            WHERE h.has_jk_detail = true
              AND h.jk_rc_cnt_t > 0
            GROUP BY h.jk_name, h.jk_no
            HAVING MAX(h.jk_rc_cnt_t) >= {min_races}
        )
        SELECT
            jk_name AS "기수명",
            total_races AS "통산출전",
            wins AS "1착",
            places AS "입상",
            win_rate AS "승률(%)",
            place_rate AS "복승률(%)",
            races_in_data AS "분석경주수"
        FROM jockey_stats
        ORDER BY win_rate DESC
        LIMIT 20
        """

        print(f"\n[상위 기수 (최소 {min_races}회 출전)]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def top_horses(self, min_races: int = 5) -> str:
        """최소 출전 횟수 이상의 말을 입상률 기준 상위로 출력합니다.

        Args:
            min_races: 최소 출전 횟수
        """
        sql = f"""
        WITH horse_stats AS (
            SELECT
                h.hr_name,
                h.hr_no,
                MAX(h.hr_rc_cnt_t) AS total_races,
                MAX(h.hr_ord1_cnt_t) AS wins,
                MAX(h.hr_ord1_cnt_t + h.hr_ord2_cnt_t + h.hr_ord3_cnt_t) AS places,
                ROUND(MAX(h.hr_win_rate_t), 1) AS win_rate,
                ROUND(MAX(h.hr_plc_rate_t), 1) AS place_rate,
                MAX(h.hr_rating) AS rating,
                COUNT(DISTINCT (h.race_date || '_' || h.race_no)) AS races_in_data
            FROM horses h
            WHERE h.has_hr_detail = true
              AND h.hr_rc_cnt_t > 0
            GROUP BY h.hr_name, h.hr_no
            HAVING MAX(h.hr_rc_cnt_t) >= {min_races}
        )
        SELECT
            hr_name AS "말이름",
            total_races AS "통산출전",
            wins AS "1착",
            places AS "입상",
            win_rate AS "승률(%)",
            place_rate AS "복승률(%)",
            rating AS "레이팅",
            races_in_data AS "분석경주수"
        FROM horse_stats
        ORDER BY place_rate DESC
        LIMIT 20
        """

        print(f"\n[상위 말 (최소 {min_races}회 출전)]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def venue_analysis(self) -> str:
        """경마장별 성과 차이 분석

        서울/부산/제주 경마장별로 배당률 상위 말의 입상률,
        평균 배당률, 경주당 평균 출전마 수 등을 비교합니다.
        """
        sql = """
        WITH odds_ranked AS (
            SELECT
                h.*,
                ROW_NUMBER() OVER (
                    PARTITION BY h.race_date, h.meet, h.race_no
                    ORDER BY h.win_odds ASC
                ) AS odds_rank
            FROM horses h
        ),
        with_result AS (
            SELECT
                o.venue,
                o.odds_rank,
                o.win_odds,
                o.race_date,
                o.meet,
                o.race_no,
                CASE WHEN r.chul_no IS NOT NULL THEN 1 ELSE 0 END AS is_top3
            FROM odds_ranked o
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON o.race_date = races.race_date
                AND o.meet = races.meet
                AND o.race_no = races.race_no
            LEFT JOIN results r
                ON o.race_date = r.race_date
                AND o.meet = r.meet
                AND o.race_no = r.race_no
                AND o.chul_no = r.chul_no
        )
        SELECT
            venue AS "경마장",
            COUNT(DISTINCT (race_date || '_' || meet || '_' || race_no)) AS "경주수",
            COUNT(*) AS "총출전",
            ROUND(AVG(win_odds), 1) AS "평균배당",
            ROUND(
                SUM(CASE WHEN odds_rank <= 3 THEN is_top3 ELSE 0 END) * 100.0
                / NULLIF(SUM(CASE WHEN odds_rank <= 3 THEN 1 ELSE 0 END), 0),
                1
            ) AS "상위3 입상률(%)",
            ROUND(
                SUM(is_top3) * 100.0 / COUNT(*), 1
            ) AS "전체 입상률(%)",
            ROUND(
                COUNT(*) * 1.0
                / NULLIF(COUNT(DISTINCT (race_date || '_' || meet || '_' || race_no)), 0),
                1
            ) AS "경주당 출전마"
        FROM with_result
        GROUP BY venue
        ORDER BY venue
        """

        print("\n[경마장별 성과 분석]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def weight_analysis(self) -> str:
        """부담중량 변화의 영향 분석

        부담중량(budam)과 부가중량(buga1)의 차이를
        입상마와 미입상마로 나누어 비교합니다.
        """
        sql = """
        WITH weight_data AS (
            SELECT
                h.budam - h.buga1 AS weight_change,
                CASE WHEN r.chul_no IS NOT NULL THEN 'winner' ELSE 'loser' END AS category
            FROM horses h
            INNER JOIN (
                SELECT DISTINCT race_date, meet, race_no FROM results
            ) races
                ON h.race_date = races.race_date
                AND h.meet = races.meet
                AND h.race_no = races.race_no
            LEFT JOIN results r
                ON h.race_date = r.race_date
                AND h.meet = r.meet
                AND h.race_no = r.race_no
                AND h.chul_no = r.chul_no
            WHERE h.budam > 0
        )
        SELECT
            category AS "구분",
            COUNT(*) AS "마리수",
            ROUND(AVG(weight_change), 2) AS "평균중량변화(kg)",
            ROUND(MEDIAN(weight_change), 2) AS "중앙값(kg)",
            ROUND(MIN(weight_change), 2) AS "최소(kg)",
            ROUND(MAX(weight_change), 2) AS "최대(kg)"
        FROM weight_data
        GROUP BY category
        ORDER BY category DESC
        """

        print("\n[부담중량 변화의 영향]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def data_availability(self) -> str:
        """데이터 가용성 통계

        상세정보(hrDetail, jkDetail, trDetail)의
        보유율을 확인합니다.
        """
        sql = """
        SELECT
            COUNT(*) AS "전체 유효마",
            SUM(CASE WHEN has_hr_detail THEN 1 ELSE 0 END) AS "말상세 보유",
            ROUND(SUM(CASE WHEN has_hr_detail THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                AS "말상세 보유율(%)",
            SUM(CASE WHEN has_jk_detail THEN 1 ELSE 0 END) AS "기수상세 보유",
            ROUND(SUM(CASE WHEN has_jk_detail THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                AS "기수상세 보유율(%)",
            SUM(CASE WHEN has_tr_detail THEN 1 ELSE 0 END) AS "조교사상세 보유",
            ROUND(SUM(CASE WHEN has_tr_detail THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                AS "조교사상세 보유율(%)"
        FROM horses
        """

        print("\n[데이터 가용성 통계]")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def custom_query(self, sql: str) -> str:
        """사용자 정의 SQL 쿼리를 실행합니다.

        Args:
            sql: 실행할 SQL 쿼리

        Returns:
            포맷된 결과 문자열
        """
        print("\n[커스텀 쿼리]")
        print(f"SQL: {sql}")
        print("-" * 60)
        result = self._execute_and_format(sql)
        print(result)
        return result

    def _execute_and_format(self, sql: str) -> str:
        """SQL을 실행하고 결과를 포맷된 테이블 문자열로 반환합니다.

        Args:
            sql: 실행할 SQL 쿼리

        Returns:
            포맷된 테이블 문자열
        """
        try:
            result = self.conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            if not rows:
                return "(결과 없음)"

            # 각 열의 최대 너비 계산
            col_widths = []
            for i, col_name in enumerate(columns):
                max_width = len(col_name)
                for row in rows:
                    cell = str(row[i]) if row[i] is not None else "NULL"
                    max_width = max(max_width, len(cell))
                col_widths.append(min(max_width, 20))  # 최대 20자

            # 헤더
            header = "  ".join(
                str(col).ljust(col_widths[i]) for i, col in enumerate(columns)
            )
            separator = "  ".join("-" * w for w in col_widths)

            # 행
            formatted_rows = []
            for row in rows:
                cells = []
                for i, cell in enumerate(row):
                    cell_str = str(cell) if cell is not None else "NULL"
                    if len(cell_str) > 20:
                        cell_str = cell_str[:17] + "..."
                    cells.append(cell_str.ljust(col_widths[i]))
                formatted_rows.append("  ".join(cells))

            lines = [header, separator] + formatted_rows
            return "\n".join(lines)

        except Exception as e:
            return f"[ERROR] 쿼리 실행 실패: {e}"

    def close(self):
        """DuckDB 연결을 종료합니다."""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="DuckDB 기반 경마 데이터 분석 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python3 data_analysis/duckdb_loader.py                          # 전체 분석
  python3 data_analysis/duckdb_loader.py --analysis odds          # 배당률 분석만
  python3 data_analysis/duckdb_loader.py --analysis jockey        # 기수 분석만
  python3 data_analysis/duckdb_loader.py --analysis horse         # 말 분석만
  python3 data_analysis/duckdb_loader.py --analysis venue         # 경마장별 분석
  python3 data_analysis/duckdb_loader.py --query "SELECT * FROM horses LIMIT 5"
        """,
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="데이터 디렉토리 경로 (기본값: data)",
    )
    parser.add_argument(
        "--query",
        help="커스텀 SQL 쿼리 (horses, results 테이블 사용 가능)",
    )
    parser.add_argument(
        "--analysis",
        choices=["odds", "jockey", "horse", "venue", "weight", "availability", "all"],
        default="all",
        help="분석 유형 선택 (기본값: all)",
    )
    parser.add_argument(
        "--min-jockey-races",
        type=int,
        default=10,
        help="상위 기수 분석 시 최소 출전 횟수 (기본값: 10)",
    )
    parser.add_argument(
        "--min-horse-races",
        type=int,
        default=5,
        help="상위 말 분석 시 최소 출전 횟수 (기본값: 5)",
    )

    args = parser.parse_args()

    analyzer = RaceDataAnalyzer(args.data_dir)

    try:
        if args.query:
            analyzer.custom_query(args.query)
        elif args.analysis == "all":
            analyzer.odds_rank_analysis()
            analyzer.jockey_performance()
            analyzer.horse_performance()
            analyzer.venue_analysis()
            analyzer.weight_analysis()
            analyzer.data_availability()
            analyzer.top_jockeys(min_races=args.min_jockey_races)
            analyzer.top_horses(min_races=args.min_horse_races)
        elif args.analysis == "odds":
            analyzer.odds_rank_analysis()
        elif args.analysis == "jockey":
            analyzer.jockey_performance()
            analyzer.top_jockeys(min_races=args.min_jockey_races)
        elif args.analysis == "horse":
            analyzer.horse_performance()
            analyzer.top_horses(min_races=args.min_horse_races)
        elif args.analysis == "venue":
            analyzer.venue_analysis()
        elif args.analysis == "weight":
            analyzer.weight_analysis()
        elif args.analysis == "availability":
            analyzer.data_availability()
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
