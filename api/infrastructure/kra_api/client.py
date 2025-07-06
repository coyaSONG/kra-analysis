import httpx
from typing import Optional, List, Dict, Any
import asyncio
from urllib.parse import unquote
from config import settings
import structlog
import xml.etree.ElementTree as ET
import warnings
import os
import json
from datetime import datetime
from pathlib import Path

# SSL 경고 비활성화
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


logger = structlog.get_logger()


class KRAApiClient:
    def __init__(self):
        self.base_url = settings.kra_api_base_url
        self.api_key = settings.kra_api_key
        self.timeout = settings.kra_api_timeout
        self.max_retries = settings.kra_api_max_retries
        
        # API 엔드포인트별 경로
        self.endpoints = {
            "race_detail": "/API214_1/RaceDetailResult_1",
            "race_result": "/API299/Race_Result_total",
            "horse_detail": "/API8_2/raceHorseInfo_2",
            "jockey_detail": "/API12_1/jockeyInfo_1",
            "trainer_detail": "/API19_1/trainerInfo_1"
        }
        
        # 경마장 매핑
        self.meet_names = {'1': '서울', '2': '제주', '3': '부산경남'}
        self.meet_folders = {'1': 'seoul', '2': 'jeju', '3': 'busan'}
        
        # 데이터 저장 경로
        self.data_base_path = Path("data")
        self.cache_base_path = self.data_base_path / "cache"
    
    def _xml_to_dict(self, element) -> Dict[str, Any]:
        """XML Element를 딕셔너리로 변환합니다."""
        result = {}
        
        # 속성 처리
        if element.attrib:
            result.update(element.attrib)
        
        # 텍스트 내용이 있는 경우
        if element.text and element.text.strip():
            # 자식 요소가 없으면 텍스트만 반환
            if not list(element):
                return element.text.strip()
            else:
                result['text'] = element.text.strip()
        
        # 자식 요소 처리
        children = {}
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in children:
                # 같은 태그가 여러 개인 경우 리스트로 처리
                if not isinstance(children[child.tag], list):
                    children[child.tag] = [children[child.tag]]
                children[child.tag].append(child_data)
            else:
                children[child.tag] = child_data
        
        result.update(children)
        return result if result else None
        
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """KRA API에 요청을 보내고 응답을 반환합니다."""
        url = f"{self.base_url}{endpoint}"
        
        # 서비스 키 추가 (URL 디코딩 필요)
        params["serviceKey"] = unquote(self.api_key) if self.api_key else None
        
        # JSON 응답 요청
        params["_type"] = "json"
        
        # httpx 클라이언트 설정
        # KRA API는 특정 SSL/TLS 설정이 필요함
        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=False,  # SSL 검증 비활성화 (정부 API 호환성)
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            # HTTP/2 비활성화 (일부 정부 API와 호환성 문제)
            http2=False
        ) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    # JSON 응답 처리
                    if params.get("_type") == "json":
                        return response.json()
                    
                    # XML 응답 처리 (fallback)
                    root = ET.fromstring(response.text)
                    return self._xml_to_dict(root)
                    
                except httpx.HTTPError as e:
                    logger.warning(
                        "KRA API request failed",
                        endpoint=endpoint,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
    
    async def get_race_detail(self, date: str, meet: int, race_no: int) -> Optional[Dict[str, Any]]:
        """특정 경주의 상세 데이터를 가져옵니다."""
        params = {
            "numOfRows": "50",
            "pageNo": "1",
            "meet": str(meet),
            "rc_date": date,
            "rc_no": str(race_no)
        }
        
        try:
            response = await self._make_request(self.endpoints["race_detail"], params)
            
            # 응답 검증
            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    return self._process_race_detail(body["items"], date, meet, race_no)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get race detail", date=date, meet=meet, race_no=race_no, error=str(e))
            return None
    
    def _process_race_detail(self, items: Dict[str, Any], date: str, meet: int, race_no: int) -> Dict[str, Any]:
        """경주 상세 데이터를 처리합니다."""
        horses = items.get("item", [])
        if not isinstance(horses, list):
            horses = [horses]
        
        # 첫 번째 말 데이터에서 경주 정보 추출
        first_horse = horses[0] if horses else {}
        
        race_info = {
            "date": date,
            "meet": meet,
            "race_no": race_no,
            "race_name": first_horse.get("rcName", ""),
            "distance": first_horse.get("rcDist", 0),
            "track_condition": first_horse.get("track", ""),
            "weather": first_horse.get("weather", ""),
            "race_time": first_horse.get("rcTime", 0),
            "horses": []
        }
        
        # 말 정보 처리
        for horse in horses:
            horse_info = {
                "chul_no": horse.get("chulNo", 0),
                "horse_no": horse.get("hrNo", ""),
                "horse_name": horse.get("hrName", ""),
                "age": horse.get("age", 0),
                "sex": horse.get("sex", ""),
                "weight": horse.get("wgHr", ""),
                "jockey_no": horse.get("jkNo", ""),
                "jockey_name": horse.get("jkName", ""),
                "trainer_no": horse.get("trNo", ""),
                "trainer_name": horse.get("trName", ""),
                "owner_no": horse.get("owNo", ""),
                "owner_name": horse.get("owName", ""),
                "win_odds": float(horse.get("winOdds", 0)),
                "plc_odds": float(horse.get("plcOdds", 0)),
                "ord": horse.get("ord", 0),
                "wg_budam": horse.get("wgBudam", 0),
                "rating": horse.get("rating", 0)
            }
            race_info["horses"].append(horse_info)
        
        return race_info
    
    async def get_all_races(self, date: str, meet: int) -> List[Dict[str, Any]]:
        """특정 날짜의 모든 경주 데이터를 가져옵니다."""
        races = []
        
        # 일반적으로 1일 최대 15경주
        for race_no in range(1, 16):
            try:
                race_data = await self.get_race_detail(date, meet, race_no)
                if race_data:
                    races.append(race_data)
                else:
                    # 데이터가 없으면 중단
                    break
                    
                # API 호출 제한 방지
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to get race {race_no}", error=str(e))
                break
        
        return races
    
    async def get_horse_detail(self, horse_no: str) -> Optional[Dict[str, Any]]:
        """말의 상세 정보를 가져옵니다."""
        params = {
            "pageNo": "1",
            "numOfRows": "10",
            "hr_no": horse_no
        }
        
        try:
            response = await self._make_request(self.endpoints["horse_detail"], params)
            
            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get horse detail", horse_no=horse_no, error=str(e))
            return None
    
    async def get_jockey_detail(self, jockey_no: str) -> Optional[Dict[str, Any]]:
        """기수의 상세 정보를 가져옵니다."""
        params = {
            "pageNo": "1",
            "numOfRows": "10", 
            "jk_no": jockey_no
        }
        
        try:
            response = await self._make_request(self.endpoints["jockey_detail"], params)
            
            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get jockey detail", jockey_no=jockey_no, error=str(e))
            return None
    
    async def get_trainer_detail(self, trainer_no: str) -> Optional[Dict[str, Any]]:
        """조교사의 상세 정보를 가져옵니다."""
        params = {
            "pageNo": "1",
            "numOfRows": "10",
            "tr_no": trainer_no
        }
        
        try:
            response = await self._make_request(self.endpoints["trainer_detail"], params)
            
            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get trainer detail", trainer_no=trainer_no, error=str(e))
            return None