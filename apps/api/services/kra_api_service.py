"""
KRA API 클라이언트 서비스
KRA 공공 API와의 모든 통신 처리
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log
)

from config import settings
from infrastructure.redis_client import CacheService

logger = structlog.get_logger()


class KRAAPIError(Exception):
    """KRA API 관련 오류"""
    pass


class KRAAPIService:
    """KRA API 통신 서비스"""
    
    def __init__(self):
        # Decode the API key if it's URL encoded
        from urllib.parse import unquote
        self.base_url = settings.kra_api_base_url
        self.api_key = unquote(settings.kra_api_key)
        self.timeout = settings.kra_api_timeout
        # Don't initialize cache service in constructor
        self._cache_service = None
        
        # HTTP 클라이언트 설정
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Accept": "application/json",
                "User-Agent": f"{settings.app_name}/{settings.version}"
            }
        )
    
    @property
    def cache_service(self):
        """Lazy load cache service"""
        if self._cache_service is None:
            self._cache_service = CacheService()
        return self._cache_service
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, KRAAPIError))
    )
    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        KRA API 요청 실행
        
        Args:
            endpoint: API 엔드포인트
            method: HTTP 메서드
            params: 쿼리 파라미터
            data: 요청 바디 데이터
            
        Returns:
            API 응답 데이터
        """
        url = f"{self.base_url}/{endpoint}"
        
        # API 키 추가
        if params is None:
            params = {}
        params["serviceKey"] = self.api_key
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
            
            # 응답 검증
            response.raise_for_status()
            
            # JSON 파싱
            result = response.json()
            
            # KRA API 오류 체크
            if result.get("status") == "error":
                raise KRAAPIError(f"KRA API error: {result.get('message', 'Unknown error')}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "KRA API HTTP error",
                status_code=e.response.status_code,
                url=str(e.request.url),
                response_text=e.response.text[:500]
            )
            raise KRAAPIError(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            
        except httpx.HTTPError as e:
            logger.error("KRA API connection error", error=str(e))
            raise KRAAPIError(f"Connection error: {str(e)}")
            
        except Exception as e:
            logger.error("Unexpected error in KRA API request", error=str(e))
            raise KRAAPIError(f"Unexpected error: {str(e)}")
    
    async def get_race_info(
        self,
        race_date: str,
        meet: str,
        race_no: int,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        경주 정보 조회 (API214_1 - 경주 상세 결과)
        
        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드 (1: 서울, 2: 제주, 3: 부산)
            race_no: 경주 번호
            use_cache: 캐시 사용 여부
            
        Returns:
            경주 정보
        """
        cache_key = f"race_info:{race_date}:{meet}:{race_no}"
        
        # 캐시 확인
        if use_cache:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info("Using cached race info", key=cache_key)
                return cached_data
        
        # API 호출
        params = {
            "meet": meet,
            "rc_date": race_date,
            "rc_no": race_no,
            "numOfRows": 50,
            "pageNo": 1,
            "_type": "json"
        }
        
        # Use correct endpoint from KRA API documentation
        result = await self._make_request(
            endpoint="API214_1/RaceDetailResult_1",
            params=params
        )
        
        # 캐시 저장 (1시간)
        if use_cache:
            try:
                await self.cache_service.set(cache_key, result, ttl=3600)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
    
    async def get_race_result(
        self,
        race_date: str,
        meet: str,
        race_no: int,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        경주 결과 조회 (get_race_info와 동일 - API214_1 사용)
        
        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드
            race_no: 경주 번호
            use_cache: 캐시 사용 여부
            
        Returns:
            경주 결과
        """
        # get_race_info와 동일한 API 사용
        return await self.get_race_info(race_date, meet, race_no, use_cache)
    
    async def get_horse_info(
        self,
        horse_no: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        마필 정보 조회 (API8_2 - 경주마 상세정보)
        
        Args:
            horse_no: 마번
            use_cache: 캐시 사용 여부
            
        Returns:
            마필 정보
        """
        cache_key = f"horse_info:{horse_no}"
        
        # 캐시 확인
        if use_cache:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info("Using cached horse info", key=cache_key)
                return cached_data
        
        # API 호출
        params = {
            "hr_no": horse_no,
            "pageNo": 1,
            "numOfRows": 10,
            "_type": "json"
        }
        
        result = await self._make_request(
            endpoint="API8_2/raceHorseInfo_2",
            params=params
        )
        
        # 캐시 저장 (24시간)
        if use_cache:
            try:
                await self.cache_service.set(cache_key, result, ttl=86400)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
    
    async def get_jockey_info(
        self,
        jockey_no: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        기수 정보 조회 (API12_1 - 기수 정보)
        
        Args:
            jockey_no: 기수 번호
            use_cache: 캐시 사용 여부
            
        Returns:
            기수 정보
        """
        cache_key = f"jockey_info:{jockey_no}"
        
        # 캐시 확인
        if use_cache:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info("Using cached jockey info", key=cache_key)
                return cached_data
        
        # API 호출
        params = {
            "jk_no": jockey_no,
            "numOfRows": 100,
            "pageNo": 1,
            "_type": "json"
        }
        
        result = await self._make_request(
            endpoint="API12_1/jockeyInfo_1",
            params=params
        )
        
        # 캐시 저장 (24시간)
        if use_cache:
            try:
                await self.cache_service.set(cache_key, result, ttl=86400)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
    
    async def get_trainer_info(
        self,
        trainer_no: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        조교사 정보 조회 (API19_1 - 조교사 정보)
        
        Args:
            trainer_no: 조교사 번호
            use_cache: 캐시 사용 여부
            
        Returns:
            조교사 정보
        """
        cache_key = f"trainer_info:{trainer_no}"
        
        # 캐시 확인
        if use_cache:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info("Using cached trainer info", key=cache_key)
                return cached_data
        
        # API 호출
        params = {
            "tr_no": trainer_no,
            "pageNo": 1,
            "numOfRows": 10,
            "_type": "json"
        }
        
        result = await self._make_request(
            endpoint="API19_1/trainerInfo_1",
            params=params
        )
        
        # 캐시 저장 (24시간)
        if use_cache:
            try:
                await self.cache_service.set(cache_key, result, ttl=86400)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
    
    async def get_odds_from_race_info(
        self,
        race_date: str,
        meet: str,
        race_no: int,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        경주 정보에서 배당률 추출
        
        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_no: 경주 번호
            use_cache: 캐시 사용 여부
            
        Returns:
            배당률 정보
        """
        # 경주 정보 조회
        race_info = await self.get_race_info(race_date, meet, race_no, use_cache)
        
        # 배당률 정보 추출
        odds_data = {
            "race_date": race_date,
            "meet": meet,
            "race_no": race_no,
            "horses": []
        }
        
        if race_info and "response" in race_info and "body" in race_info["response"]:
            items = race_info["response"]["body"].get("items", {})
            if items and "item" in items:
                horses = items["item"]
                if not isinstance(horses, list):
                    horses = [horses]
                
                for horse in horses:
                    odds_data["horses"].append({
                        "hr_no": horse.get("hrNo"),
                        "hr_name": horse.get("hrName"),
                        "chul_no": horse.get("chulNo"),
                        "win_odds": horse.get("winOdds", 0),
                        "plc_odds": horse.get("plcOdds", 0),
                        "ord": horse.get("ord", 0)
                    })
        
        return odds_data
    
    async def get_weather_info(
        self,
        race_date: str,
        meet: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        날씨 정보 조회 (현재 KRA API에서 제공하지 않음)
        
        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            use_cache: 캐시 사용 여부
            
        Returns:
            날씨 정보 (빈 딕셔너리)
        """
        # KRA API에서 날씨 정보를 제공하지 않으므로 빈 딕셔너리 반환
        return {
            "race_date": race_date,
            "meet": meet,
            "weather_data": None,
            "note": "Weather information is not available from KRA API"
        }
    
    async def batch_get_race_results(
        self,
        race_date: str,
        meet: str,
        race_numbers: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """
        여러 경주 결과 일괄 조회
        
        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_numbers: 경주 번호 리스트
            
        Returns:
            경주 번호별 결과 딕셔너리
        """
        tasks = []
        for race_no in race_numbers:
            task = self.get_race_result(race_date, meet, race_no)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        race_results = {}
        for race_no, result in zip(race_numbers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to get race result",
                    race_no=race_no,
                    error=str(result)
                )
                race_results[race_no] = None
            else:
                race_results[race_no] = result
        
        return race_results


# 싱글톤 인스턴스
_kra_api_service: Optional[KRAAPIService] = None


async def get_kra_api_service() -> KRAAPIService:
    """KRA API 서비스 인스턴스 반환"""
    global _kra_api_service
    if _kra_api_service is None:
        _kra_api_service = KRAAPIService()
    return _kra_api_service
