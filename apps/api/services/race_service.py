import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from supabase import Client

from infrastructure.kra_api.client import KRAApiClient
from models.race_dto import RaceStatus

logger = structlog.get_logger()


class RaceService:
    def __init__(self, supabase: Client | None):
        self.supabase = supabase
        self.kra_client = KRAApiClient()
        self._cache = {}  # In-memory cache when Supabase is not available
        self.nodejs_api_url = "http://localhost:3001"  # Node.js 수집 서버

    async def create_collection_job(self, request) -> str:
        """수집 작업을 생성하고 job_id를 반환합니다."""
        job_id = str(uuid.uuid4())

        try:
            if self.supabase:
                self.supabase.table("collection_jobs").insert(
                    {
                        "id": job_id,
                        "date": request.date,
                        "meet": request.meet,
                        "race_no": request.race_no,
                        "status": "queued",
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ).execute()
            else:
                # In-memory storage when Supabase is not available
                if "collection_jobs" not in self._cache:
                    self._cache["collection_jobs"] = {}
                self._cache["collection_jobs"][job_id] = {
                    "id": job_id,
                    "date": request.date,
                    "meet": request.meet,
                    "race_no": request.race_no,
                    "status": "queued",
                    "created_at": datetime.now(UTC).isoformat(),
                }

            return job_id

        except Exception as e:
            logger.error("Failed to create collection job", error=str(e))
            raise

    async def process_collection(
        self, job_id: str, date: str, meet: int, race_no: int | None
    ):
        """백그라운드에서 경주 데이터를 수집합니다."""
        try:
            # 작업 시작 상태 업데이트
            if self.supabase:
                self.supabase.table("collection_jobs").update(
                    {
                        "status": "processing",
                        "started_at": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", job_id).execute()
            else:
                if (
                    "collection_jobs" in self._cache
                    and job_id in self._cache["collection_jobs"]
                ):
                    self._cache["collection_jobs"][job_id].update(
                        {
                            "status": "processing",
                            "started_at": datetime.now(UTC).isoformat(),
                        }
                    )

            # Node.js 수집 서버 호출
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.nodejs_api_url}/collect",
                        json={"date": date, "meet": meet},
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"Node.js 수집 완료: {result.get('message')}")

                        # 수집된 데이터를 Python API에서도 읽을 수 있도록
                        # 파일에서 읽거나 Node.js가 반환한 데이터 사용
                        races = []  # 필요시 파일에서 읽기
                    else:
                        raise Exception(f"수집 실패: {response.text}")

            except Exception as e:
                logger.warning(f"Node.js 서버 호출 실패, Python 직접 수집 시도: {e}")
                # Fallback: Python으로 직접 수집
                if race_no:
                    race_data = await self.kra_client.get_race_detail(
                        date, meet, race_no
                    )
                    races = [race_data] if race_data else []
                else:
                    races = await self.kra_client.get_all_races(date, meet)

            # 수집된 경주 수 로깅
            logger.info(f"Collected {len(races)} races for {date} meet {meet}")

            # 데이터 저장
            saved_count = 0
            for race_data in races:
                if race_data:
                    await self._save_race_data(race_data)
                    saved_count += 1

            # 작업 완료 상태 업데이트
            if self.supabase:
                self.supabase.table("collection_jobs").update(
                    {
                        "status": "completed",
                        "completed_at": datetime.now(UTC).isoformat(),
                        "race_count": saved_count,
                    }
                ).eq("id", job_id).execute()
            else:
                if (
                    "collection_jobs" in self._cache
                    and job_id in self._cache["collection_jobs"]
                ):
                    self._cache["collection_jobs"][job_id].update(
                        {
                            "status": "completed",
                            "completed_at": datetime.now(UTC).isoformat(),
                            "race_count": saved_count,
                        }
                    )

            logger.info(
                f"Collection job {job_id} completed. Saved {saved_count} races."
            )

        except Exception as e:
            logger.error("Failed to process collection", job_id=job_id, error=str(e))

            # 작업 실패 상태 업데이트
            if self.supabase:
                self.supabase.table("collection_jobs").update(
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "completed_at": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", job_id).execute()
            else:
                if (
                    "collection_jobs" in self._cache
                    and job_id in self._cache["collection_jobs"]
                ):
                    self._cache["collection_jobs"][job_id].update(
                        {
                            "status": "failed",
                            "error_message": str(e),
                            "completed_at": datetime.now(UTC).isoformat(),
                        }
                    )

    async def _save_race_data(self, race_data: dict[str, Any]):
        """경주 데이터를 데이터베이스에 저장합니다."""
        date = race_data.get("date")
        meet = race_data.get("meet")
        race_no = race_data.get("race_no")

        try:
            if self.supabase:
                # Supabase 사용 시
                # 기존 데이터 확인
                existing = (
                    self.supabase.table("races")
                    .select("id")
                    .eq("date", date)
                    .eq("meet", meet)
                    .eq("race_no", race_no)
                    .execute()
                )

                # 경주 결과 확인 (ord가 0이 아닌 말이 있으면 완료된 경주)
                is_completed = any(
                    horse.get("ord", 0) != 0 for horse in race_data.get("horses", [])
                )

                race_record = {
                    "date": date,
                    "meet": meet,
                    "race_no": race_no,
                    "race_name": race_data.get("race_name"),
                    "distance": race_data.get("distance"),
                    "grade": race_data.get("grade", ""),
                    "track_condition": race_data.get("track_condition"),
                    "weather": race_data.get("weather"),
                    "status": RaceStatus.COLLECTED,
                    "raw_data": race_data,
                    "horse_count": len(race_data.get("horses", [])),
                    "is_completed": is_completed,
                    "updated_at": datetime.now(UTC).isoformat(),
                }

                if existing.data:
                    # 업데이트
                    result = (
                        self.supabase.table("races")
                        .update(race_record)
                        .eq("id", existing.data[0]["id"])
                        .execute()
                    )
                    race_id = existing.data[0]["id"]
                else:
                    # 새로 삽입
                    race_record["id"] = str(uuid.uuid4())
                    race_record["created_at"] = datetime.now(UTC).isoformat()
                    result = self.supabase.table("races").insert(race_record).execute()
                    race_id = result.data[0]["id"] if result.data else None

                # 경주가 완료된 경우 결과 저장
                if is_completed and race_id:
                    await self._save_race_result(race_id, race_data)
            else:
                # In-memory 저장
                if "races" not in self._cache:
                    self._cache["races"] = {}

                # 경주 결과 확인
                is_completed = any(
                    horse.get("ord", 0) != 0 for horse in race_data.get("horses", [])
                )

                # 고유 키 생성 (date-meet-race_no)
                race_key = f"{date}-{meet}-{race_no}"
                race_id = str(uuid.uuid4())

                race_record = {
                    "id": race_id,
                    "date": date,
                    "meet": meet,
                    "race_no": race_no,
                    "race_name": race_data.get("race_name"),
                    "distance": race_data.get("distance"),
                    "grade": race_data.get("grade", ""),
                    "track_condition": race_data.get("track_condition"),
                    "weather": race_data.get("weather"),
                    "status": RaceStatus.COLLECTED,
                    "raw_data": race_data,
                    "horse_count": len(race_data.get("horses", [])),
                    "is_completed": is_completed,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }

                # 저장 또는 업데이트
                self._cache["races"][race_key] = race_record

                # 경주가 완료된 경우 결과 저장
                if is_completed:
                    await self._save_race_result(race_id, race_data)

        except Exception as e:
            logger.error(
                "Failed to save race data",
                date=date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            raise

    async def _save_race_result(self, race_id: str, race_data: dict[str, Any]):
        """경주 결과를 저장합니다."""
        try:
            # 1-2-3위 찾기
            horses = race_data.get("horses", [])
            sorted_horses = sorted(horses, key=lambda h: h.get("ord", 999))

            if len(sorted_horses) >= 3:
                winner = next(
                    (h["chul_no"] for h in sorted_horses if h.get("ord") == 1), None
                )
                second = next(
                    (h["chul_no"] for h in sorted_horses if h.get("ord") == 2), None
                )
                third = next(
                    (h["chul_no"] for h in sorted_horses if h.get("ord") == 3), None
                )

                if winner and second and third:
                    if self.supabase:
                        # 기존 결과 확인
                        existing = (
                            self.supabase.table("race_results")
                            .select("id")
                            .eq("race_id", race_id)
                            .execute()
                        )

                        result_record = {
                            "race_id": race_id,
                            "winner": winner,
                            "second": second,
                            "third": third,
                            "created_at": datetime.now(UTC).isoformat(),
                        }

                        if existing.data:
                            # 업데이트
                            self.supabase.table("race_results").update(
                                result_record
                            ).eq("id", existing.data[0]["id"]).execute()
                        else:
                            # 삽입
                            result_record["id"] = str(uuid.uuid4())
                            self.supabase.table("race_results").insert(
                                result_record
                            ).execute()
                    else:
                        # In-memory 저장
                        if "race_results" not in self._cache:
                            self._cache["race_results"] = {}

                        result_record = {
                            "id": str(uuid.uuid4()),
                            "race_id": race_id,
                            "winner": winner,
                            "second": second,
                            "third": third,
                            "created_at": datetime.now(UTC).isoformat(),
                        }

                        self._cache["race_results"][race_id] = result_record

        except Exception as e:
            logger.error("Failed to save race result", race_id=race_id, error=str(e))

    async def get_race(self, race_id: str) -> dict[str, Any] | None:
        """특정 경주 정보를 조회합니다."""
        try:
            if self.supabase:
                result = (
                    self.supabase.table("races").select("*").eq("id", race_id).execute()
                )
                return result.data[0] if result.data else None
            else:
                # In-memory 조회
                if "races" in self._cache:
                    for race in self._cache["races"].values():
                        if race.get("id") == race_id:
                            return race
                return None

        except Exception as e:
            logger.error("Failed to get race", race_id=race_id, error=str(e))
            raise

    async def list_races_by_date(
        self, date: str, meet: int | None = None
    ) -> list[dict[str, Any]]:
        """특정 날짜의 경주 목록을 조회합니다."""
        try:
            if self.supabase:
                query = self.supabase.table("races").select("*").eq("date", date)

                if meet:
                    query = query.eq("meet", meet)

                result = query.order("race_no").execute()
                return result.data
            else:
                # In-memory 조회
                races = []
                if "races" in self._cache:
                    for race in self._cache["races"].values():
                        if race.get("date") == date:
                            if meet is None or race.get("meet") == meet:
                                races.append(race)

                # race_no에 따라 정렬
                races.sort(key=lambda r: r.get("race_no", 0))
                return races

        except Exception as e:
            logger.error("Failed to list races", date=date, meet=meet, error=str(e))
            raise

    async def get_race_result(
        self, date: str, meet: int, race_no: int
    ) -> dict[str, Any] | None:
        """경주 결과를 조회합니다."""
        try:
            if self.supabase:
                # 먼저 race_id 찾기
                race = (
                    self.supabase.table("races")
                    .select("id")
                    .eq("date", date)
                    .eq("meet", meet)
                    .eq("race_no", race_no)
                    .execute()
                )

                if not race.data:
                    return None

                race_id = race.data[0]["id"]

                # 결과 조회
                result = (
                    self.supabase.table("race_results")
                    .select("*")
                    .eq("race_id", race_id)
                    .execute()
                )

                if result.data:
                    return {
                        "race_id": race_id,
                        "result": [
                            result.data[0]["winner"],
                            result.data[0]["second"],
                            result.data[0]["third"],
                        ],
                    }
            else:
                # In-memory 조회
                # 먼저 race 찾기
                race_key = f"{date}-{meet}-{race_no}"
                race = None

                if "races" in self._cache and race_key in self._cache["races"]:
                    race = self._cache["races"][race_key]

                if not race:
                    return None

                race_id = race.get("id")

                # 결과 조회
                if (
                    "race_results" in self._cache
                    and race_id in self._cache["race_results"]
                ):
                    result = self._cache["race_results"][race_id]
                    return {
                        "race_id": race_id,
                        "result": [result["winner"], result["second"], result["third"]],
                    }

            return None

        except Exception as e:
            logger.error(
                "Failed to get race result",
                date=date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            return None

    async def enrich_race_data(self, race_id: str):
        """경주 데이터를 보강합니다 (말, 기수, 조교사 상세 정보)."""
        try:
            # 경주 정보 조회
            race = await self.get_race(race_id)
            if not race:
                raise ValueError(f"Race not found: {race_id}")

            raw_data = race.get("raw_data", {})
            horses = raw_data.get("horses", [])

            # 각 말에 대한 상세 정보 수집
            enriched_horses = []

            for horse in horses:
                enriched_horse = horse.copy()

                # 말 상세 정보 조회
                horse_no = horse.get("horse_no")
                if horse_no:
                    horse_detail = await self._get_cached_data(
                        "horse_cache",
                        horse_no,
                        lambda horse_no=horse_no: self.kra_client.get_horse_detail(
                            horse_no
                        ),
                    )
                    if horse_detail:
                        enriched_horse["horse_detail"] = horse_detail

                # 기수 상세 정보 조회
                jockey_no = horse.get("jockey_no")
                if jockey_no:
                    jockey_detail = await self._get_cached_data(
                        "jockey_cache",
                        jockey_no,
                        lambda jockey_no=jockey_no: self.kra_client.get_jockey_detail(
                            jockey_no
                        ),
                    )
                    if jockey_detail:
                        enriched_horse["jockey_detail"] = jockey_detail

                # 조교사 상세 정보 조회
                trainer_no = horse.get("trainer_no")
                if trainer_no:
                    trainer_detail = await self._get_cached_data(
                        "trainer_cache",
                        trainer_no,
                        lambda trainer_no=trainer_no: self.kra_client.get_trainer_detail(
                            trainer_no
                        ),
                    )
                    if trainer_detail:
                        enriched_horse["trainer_detail"] = trainer_detail

                enriched_horses.append(enriched_horse)

                # API 호출 제한 방지
                await asyncio.sleep(0.5)

            # enriched_data 생성
            enriched_data = raw_data.copy()
            enriched_data["horses"] = enriched_horses
            enriched_data["enriched_at"] = datetime.now(UTC).isoformat()

            # 데이터베이스 업데이트
            self.supabase.table("races").update(
                {
                    "enriched_data": enriched_data,
                    "status": RaceStatus.ENRICHED,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", race_id).execute()

            logger.info(f"Enriched race {race_id} with {len(enriched_horses)} horses")

        except Exception as e:
            logger.error("Failed to enrich race data", race_id=race_id, error=str(e))
            # 실패 시 상태 업데이트
            self.supabase.table("races").update(
                {
                    "status": RaceStatus.FAILED,
                    "error_message": str(e),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", race_id).execute()
            raise

    async def _get_cached_data(self, cache_table: str, key: str, fetch_func):
        """캐시된 데이터를 가져오거나 새로 조회합니다."""
        try:
            # 캐시 확인
            cache_key = f"{cache_table.replace('_cache', '_no')}"
            result = (
                self.supabase.table(cache_table)
                .select("data")
                .eq(cache_key, key)
                .execute()
            )

            if result.data and result.data[0].get("data"):
                # 캐시된 데이터 반환
                return result.data[0]["data"]

            # 캐시 미스 - 새로 조회
            data = await fetch_func()

            if data:
                # 캐시 저장
                cache_record = {
                    cache_key: key,
                    "data": data,
                    "created_at": datetime.now(UTC).isoformat(),
                    "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                }

                self.supabase.table(cache_table).upsert(cache_record).execute()

            return data

        except Exception as e:
            logger.warning(
                f"Cache operation failed for {cache_table}/{key}", error=str(e)
            )
            # 캐시 실패 시 직접 조회
            return await fetch_func()

    async def get_race_status(self, race_id: str) -> dict[str, Any] | None:
        """경주의 데이터 수집 상태를 조회합니다."""
        try:
            race = await self.get_race(race_id)
            if not race:
                return None

            return {
                "race_id": race_id,
                "status": race["status"],
                "collected_at": race.get("created_at"),
                "enriched_at": (
                    race.get("updated_at")
                    if race["status"] == RaceStatus.ENRICHED
                    else None
                ),
                "horse_count": len(race.get("raw_data", {}).get("horses", [])),
                "enriched_count": (
                    len(race.get("enriched_data", {}).get("horses", []))
                    if race.get("enriched_data")
                    else 0
                ),
            }

        except Exception as e:
            logger.error("Failed to get race status", race_id=race_id, error=str(e))
            raise
