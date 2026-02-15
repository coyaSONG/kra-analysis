"""
KRA API client with retry logic and file-based caching.

Provides synchronous functions and an async client class for fetching
horse, jockey, trainer details, and race info from KRA public data APIs.

Cache: file-based in data/cache/{horses,jockeys,trainers}/ with 7-day expiry.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("KRA_API_KEY") or os.environ.get("KRA_SERVICE_KEY", "")
BASE_URL = "https://apis.data.go.kr/B551015"
CACHE_DIR = Path("data/cache")
CACHE_EXPIRY = 7 * 24 * 60 * 60  # 7 days in seconds


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def ensure_cache_dir() -> None:
    """Create cache directories if they don't exist."""
    for subdir in ("horses", "jockeys", "trainers", "results"):
        (CACHE_DIR / subdir).mkdir(parents=True, exist_ok=True)


def get_from_cache(cache_type: str, cache_id: str) -> dict | None:
    """Read data from file cache if not expired."""
    cache_path = CACHE_DIR / cache_type / f"{cache_id}.json"
    try:
        stat = cache_path.stat()
        if time.time() - stat.st_mtime > CACHE_EXPIRY:
            return None
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_to_cache(cache_type: str, cache_id: str, data: dict | list) -> None:
    """Save data to file cache."""
    cache_path = CACHE_DIR / cache_type / f"{cache_id}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# HTTP retry helper (sync)
# ---------------------------------------------------------------------------


def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> httpx.Response:
    """Fetch URL with exponential backoff retry on failure or 429 status."""
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=30.0)

            if response.status_code == 429:
                retry_delay = initial_delay * (2**attempt)
                print(
                    f"  API rate limit reached. Retrying in {retry_delay}s... "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_delay)
                continue

            return response
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                retry_delay = initial_delay * (2**attempt)
                print(
                    f"  Request failed. Retrying in {retry_delay}s... "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_delay)

    raise last_error  # type: ignore[misc]


def _is_success(data: dict) -> bool:
    """Check if KRA API response indicates success."""
    items = data.get("response", {}).get("body", {}).get("items")
    return (
        data.get("response", {}).get("header", {}).get("resultCode") == "00"
        and isinstance(items, dict)
        and items.get("item") is not None
    )


# ---------------------------------------------------------------------------
# Sync API functions
# ---------------------------------------------------------------------------


def get_race_info(meet: str, rc_date: str, rc_no: int) -> dict | None:
    """Fetch race info from API214_1 (RaceDetailResult_1).

    Args:
        meet: Meet code (1=Seoul, 2=Jeju, 3=Busan).
        rc_date: Race date in YYYYMMDD format.
        rc_no: Race number.

    Returns:
        Full API response dict, or None on failure.
    """
    url = (
        f"{BASE_URL}/API214_1/RaceDetailResult_1"
        f"?serviceKey={API_KEY}&numOfRows=50&pageNo=1"
        f"&meet={meet}&rc_date={rc_date}&rc_no={rc_no}&_type=json"
    )
    try:
        response = fetch_with_retry(url)
        data = response.json()
        if _is_success(data):
            return data
        return None
    except Exception as e:
        print(f"[ERROR] Race info fetch failed ({meet}/{rc_date}/{rc_no}R): {e}")
        return None


def get_race_result(meet: str, rc_date: str, rc_no: int) -> dict | None:
    """Fetch race result (same endpoint as get_race_info for API214_1)."""
    return get_race_info(meet, rc_date, rc_no)


def get_horse_detail(hr_no: str, hr_name: str) -> dict | None:
    """Fetch horse detail from API8_2 (raceHorseInfo_2) with caching."""
    cached = get_from_cache("horses", hr_no)
    if cached is not None:
        print(f"  [cache] Horse {hr_name} ({hr_no})")
        return cached

    url = (
        f"{BASE_URL}/API8_2/raceHorseInfo_2"
        f"?ServiceKey={API_KEY}&pageNo=1&numOfRows=10&hr_no={hr_no}&_type=json"
    )

    try:
        print(f"  [API] Horse {hr_name} ({hr_no})")
        response = fetch_with_retry(url, max_retries=3, initial_delay=1.0)
        data = response.json()

        if _is_success(data):
            horse = data["response"]["body"]["items"]["item"]
            horse_detail = _extract_horse_detail(horse)
            save_to_cache("horses", hr_no, horse_detail)
            return horse_detail
    except Exception as e:
        print(f"  [ERROR] Horse info fetch failed ({hr_no}): {e}")

    return None


def get_jockey_detail(jk_no: str, jk_name: str) -> dict | None:
    """Fetch jockey detail from API12_1 (jockeyInfo_1) with caching."""
    cached = get_from_cache("jockeys", jk_no)
    if cached is not None:
        print(f"  [cache] Jockey {jk_name} ({jk_no})")
        return cached

    url = (
        f"{BASE_URL}/API12_1/jockeyInfo_1"
        f"?serviceKey={API_KEY}&numOfRows=100&pageNo=1&jk_no={jk_no}&_type=json"
    )

    try:
        print(f"  [API] Jockey {jk_name} ({jk_no})")
        response = fetch_with_retry(url, max_retries=3, initial_delay=0.8)
        data = response.json()

        if _is_success(data):
            jockey = data["response"]["body"]["items"]["item"]
            jockey_detail = _extract_jockey_detail(jockey)
            save_to_cache("jockeys", jk_no, jockey_detail)
            return jockey_detail
    except Exception as e:
        print(f"  [ERROR] Jockey info fetch failed ({jk_no}): {e}")

    return None


def get_trainer_detail(tr_no: str, tr_name: str) -> dict | None:
    """Fetch trainer detail from API19_1 (trainerInfo_1) with caching."""
    cached = get_from_cache("trainers", tr_no)
    if cached is not None:
        print(f"  [cache] Trainer {tr_name} ({tr_no})")
        return cached

    url = (
        f"{BASE_URL}/API19_1/trainerInfo_1"
        f"?ServiceKey={API_KEY}&pageNo=1&numOfRows=10&tr_no={tr_no}&_type=json"
    )

    try:
        print(f"  [API] Trainer {tr_name} ({tr_no})")
        response = fetch_with_retry(url, max_retries=3, initial_delay=0.8)
        data = response.json()

        if _is_success(data):
            trainer = data["response"]["body"]["items"]["item"]
            trainer_detail = _extract_trainer_detail(trainer)
            save_to_cache("trainers", tr_no, trainer_detail)
            return trainer_detail
    except Exception as e:
        print(f"  [ERROR] Trainer info fetch failed ({tr_no}): {e}")

    return None


# ---------------------------------------------------------------------------
# Data extraction helpers (shared between sync and async)
# ---------------------------------------------------------------------------


def _extract_horse_detail(horse: dict) -> dict:
    """Extract and compute horse detail fields from API response."""
    rc_cnt_t = horse.get("rcCntT") or 0
    ord1_cnt_t = horse.get("ord1CntT") or 0
    ord2_cnt_t = horse.get("ord2CntT") or 0
    rc_cnt_y = horse.get("rcCntY") or 0
    ord1_cnt_y = horse.get("ord1CntY") or 0

    return {
        "faHrName": horse.get("faHrName") or "",
        "faHrNo": horse.get("faHrNo") or "",
        "moHrName": horse.get("moHrName") or "",
        "moHrNo": horse.get("moHrNo") or "",
        "rcCntT": rc_cnt_t,
        "ord1CntT": ord1_cnt_t,
        "ord2CntT": ord2_cnt_t,
        "ord3CntT": horse.get("ord3CntT") or 0,
        "rcCntY": rc_cnt_y,
        "ord1CntY": ord1_cnt_y,
        "ord2CntY": horse.get("ord2CntY") or 0,
        "ord3CntY": horse.get("ord3CntY") or 0,
        "chaksunT": horse.get("chaksunT") or 0,
        "rating": horse.get("rating") or 0,
        "hrLastAmt": horse.get("hrLastAmt") or "",
        "winRateT": round(ord1_cnt_t / rc_cnt_t * 100, 1) if rc_cnt_t > 0 else 0,
        "plcRateT": (
            round((ord1_cnt_t + ord2_cnt_t) / rc_cnt_t * 100, 1) if rc_cnt_t > 0 else 0
        ),
        "winRateY": round(ord1_cnt_y / rc_cnt_y * 100, 1) if rc_cnt_y > 0 else 0,
    }


def _extract_jockey_detail(jockey: dict) -> dict:
    """Extract and compute jockey detail fields from API response."""
    rc_cnt_t = int(jockey.get("rcCntT") or 0)
    ord1_cnt_t = int(jockey.get("ord1CntT") or 0)
    ord2_cnt_t = int(jockey.get("ord2CntT") or 0)
    rc_cnt_y = int(jockey.get("rcCntY") or 0)
    ord1_cnt_y = int(jockey.get("ord1CntY") or 0)

    return {
        "age": jockey.get("age") or "",
        "birthday": jockey.get("birthday") or "",
        "debut": jockey.get("debut") or "",
        "part": jockey.get("part") or "",
        "ord1CntT": ord1_cnt_t,
        "ord2CntT": ord2_cnt_t,
        "ord3CntT": int(jockey.get("ord3CntT") or 0),
        "rcCntT": rc_cnt_t,
        "ord1CntY": ord1_cnt_y,
        "ord2CntY": int(jockey.get("ord2CntY") or 0),
        "ord3CntY": int(jockey.get("ord3CntY") or 0),
        "rcCntY": rc_cnt_y,
        "winRateT": round(ord1_cnt_t / rc_cnt_t * 100, 1) if rc_cnt_t > 0 else 0,
        "plcRateT": (
            round((ord1_cnt_t + ord2_cnt_t) / rc_cnt_t * 100, 1) if rc_cnt_t > 0 else 0
        ),
        "winRateY": round(ord1_cnt_y / rc_cnt_y * 100, 1) if rc_cnt_y > 0 else 0,
    }


def _extract_trainer_detail(trainer: dict) -> dict:
    """Extract trainer detail fields from API response."""
    return {
        "meet": trainer.get("meet") or "",
        "part": trainer.get("part") or 0,
        "stDate": trainer.get("stDate") or 0,
        "rcCntT": trainer.get("rcCntT") or 0,
        "ord1CntT": trainer.get("ord1CntT") or 0,
        "ord2CntT": trainer.get("ord2CntT") or 0,
        "ord3CntT": trainer.get("ord3CntT") or 0,
        "winRateT": trainer.get("winRateT") or 0,
        "plcRateT": trainer.get("plcRateT") or 0,
        "qnlRateT": trainer.get("qnlRateT") or 0,
        "rcCntY": trainer.get("rcCntY") or 0,
        "ord1CntY": trainer.get("ord1CntY") or 0,
        "ord2CntY": trainer.get("ord2CntY") or 0,
        "ord3CntY": trainer.get("ord3CntY") or 0,
        "winRateY": trainer.get("winRateY") or 0,
        "plcRateY": trainer.get("plcRateY") or 0,
        "qnlRateY": trainer.get("qnlRateY") or 0,
    }


# ---------------------------------------------------------------------------
# Async API client
# ---------------------------------------------------------------------------


class AsyncKRAClient:
    """Async KRA API client with httpx.AsyncClient and concurrency control.

    Usage::

        async with AsyncKRAClient(concurrency=5) as client:
            detail = await client.get_horse_detail("2024F001", "HorseName")
    """

    def __init__(self, concurrency: int = 5):
        self._semaphore = asyncio.Semaphore(concurrency)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncKRAClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _fetch_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        initial_delay: float = 1.0,
    ) -> httpx.Response:
        """Async fetch with exponential backoff and concurrency limiting."""
        client = await self._get_client()
        last_error: Exception | None = None

        async with self._semaphore:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    if response.status_code == 429:
                        retry_delay = initial_delay * (2**attempt)
                        await asyncio.sleep(retry_delay)
                        continue
                    return response
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        retry_delay = initial_delay * (2**attempt)
                        await asyncio.sleep(retry_delay)

        raise last_error  # type: ignore[misc]

    async def get_race_info(self, meet: str, rc_date: str, rc_no: int) -> dict | None:
        """Async version of get_race_info."""
        url = (
            f"{BASE_URL}/API214_1/RaceDetailResult_1"
            f"?serviceKey={API_KEY}&numOfRows=50&pageNo=1"
            f"&meet={meet}&rc_date={rc_date}&rc_no={rc_no}&_type=json"
        )
        try:
            response = await self._fetch_with_retry(url)
            data = response.json()
            if _is_success(data):
                return data
            return None
        except Exception as e:
            print(f"[ERROR] Race info fetch failed ({meet}/{rc_date}/{rc_no}R): {e}")
            return None

    async def get_horse_detail(self, hr_no: str, hr_name: str) -> dict | None:
        """Async version of get_horse_detail with caching."""
        cached = get_from_cache("horses", hr_no)
        if cached is not None:
            return cached

        url = (
            f"{BASE_URL}/API8_2/raceHorseInfo_2"
            f"?ServiceKey={API_KEY}&pageNo=1&numOfRows=10&hr_no={hr_no}&_type=json"
        )
        try:
            response = await self._fetch_with_retry(url)
            data = response.json()
            if _is_success(data):
                horse = data["response"]["body"]["items"]["item"]
                detail = _extract_horse_detail(horse)
                save_to_cache("horses", hr_no, detail)
                return detail
        except Exception as e:
            print(f"  [ERROR] Horse info fetch failed ({hr_no}): {e}")
        return None

    async def get_jockey_detail(self, jk_no: str, jk_name: str) -> dict | None:
        """Async version of get_jockey_detail with caching."""
        cached = get_from_cache("jockeys", jk_no)
        if cached is not None:
            return cached

        url = (
            f"{BASE_URL}/API12_1/jockeyInfo_1"
            f"?serviceKey={API_KEY}&numOfRows=100&pageNo=1&jk_no={jk_no}&_type=json"
        )
        try:
            response = await self._fetch_with_retry(url)
            data = response.json()
            if _is_success(data):
                jockey = data["response"]["body"]["items"]["item"]
                detail = _extract_jockey_detail(jockey)
                save_to_cache("jockeys", jk_no, detail)
                return detail
        except Exception as e:
            print(f"  [ERROR] Jockey info fetch failed ({jk_no}): {e}")
        return None

    async def get_trainer_detail(self, tr_no: str, tr_name: str) -> dict | None:
        """Async version of get_trainer_detail with caching."""
        cached = get_from_cache("trainers", tr_no)
        if cached is not None:
            return cached

        url = (
            f"{BASE_URL}/API19_1/trainerInfo_1"
            f"?ServiceKey={API_KEY}&pageNo=1&numOfRows=10&tr_no={tr_no}&_type=json"
        )
        try:
            response = await self._fetch_with_retry(url)
            data = response.json()
            if _is_success(data):
                trainer = data["response"]["body"]["items"]["item"]
                detail = _extract_trainer_detail(trainer)
                save_to_cache("trainers", tr_no, detail)
                return detail
        except Exception as e:
            print(f"  [ERROR] Trainer info fetch failed ({tr_no}): {e}")
        return None
