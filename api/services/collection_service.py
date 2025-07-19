"""
데이터 수집 서비스
경주 데이터 수집, 전처리, 강화 로직
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
import pandas as pd
import numpy as np

from services.kra_api_service import KRAAPIService
from infrastructure.database import get_db
from infrastructure.redis_client import CacheService
from models.database_models import Race
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

logger = structlog.get_logger()


class CollectionService:
    """데이터 수집 및 처리 서비스"""
    
    def __init__(self, kra_api_service: KRAAPIService):
        self.kra_api = kra_api_service
        self.cache_service = CacheService()
    
    async def collect_race_data(
        self,
        race_date: str,
        meet: int,
        race_no: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        단일 경주 데이터 수집
        
        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드
            race_no: 경주 번호
            db: 데이터베이스 세션
            
        Returns:
            수집된 경주 데이터
        """
        try:
            logger.info(
                "Starting race data collection",
                race_date=race_date,
                meet=meet,
                race_no=race_no
            )
            
            # 기본 경주 정보 수집
            race_info = await self.kra_api.get_race_info(race_date, str(meet), race_no)
            
            # 날씨 정보 수집 (현재 API에서 제공하지 않음)
            weather_info = {}
            
            # 마필별 상세 정보 수집
            horses_data = []
            if race_info and "response" in race_info and "body" in race_info["response"]:
                items = race_info["response"]["body"].get("items", {})
                if items and "item" in items:
                    horses = items["item"]
                    if not isinstance(horses, list):
                        horses = [horses]
                    
                    for horse in horses:
                        horse_detail = await self._collect_horse_details(horse)
                        horses_data.append(horse_detail)
            
            # 데이터 통합
            collected_data = {
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "race_info": race_info,
                "weather": weather_info,
                "horses": horses_data,
                "collected_at": datetime.utcnow().isoformat()
            }
            
            # 데이터베이스 저장
            await self._save_race_data(collected_data, db)
            
            logger.info(
                "Race data collection completed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                horses_count=len(horses_data)
            )
            
            return collected_data
            
        except Exception as e:
            logger.error(
                "Race data collection failed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(e)
            )
            raise
    
    async def _collect_horse_details(
        self,
        horse_basic: Dict[str, Any]
    ) -> Dict[str, Any]:
        """마필 상세 정보 수집"""
        try:
            # 마필 정보
            horse_no = horse_basic.get("hrNo")
            horse_info = await self.kra_api.get_horse_info(horse_no) if horse_no else None
            
            # 기수 정보
            jockey_no = horse_basic.get("jkNo")
            jockey_info = await self.kra_api.get_jockey_info(jockey_no) if jockey_no else None
            
            # 조교사 정보
            trainer_no = horse_basic.get("trNo")
            trainer_info = await self.kra_api.get_trainer_info(trainer_no) if trainer_no else None
            
            # 통합
            return {
                **horse_basic,
                "horse_detail": horse_info,
                "jockey_detail": jockey_info,
                "trainer_detail": trainer_info
            }
            
        except Exception as e:
            logger.warning(
                "Failed to collect horse details",
                horse_no=horse_basic.get("horse_no"),
                error=str(e)
            )
            return horse_basic
    
    async def _save_race_data(
        self,
        data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """경주 데이터 데이터베이스 저장"""
        try:
            # 기존 데이터 확인
            existing = await db.execute(
                select(Race).where(
                    and_(
                        Race.race_date == data["race_date"],
                        Race.meet == data["meet"],
                        Race.race_no == data["race_no"]
                    )
                )
            )
            race = existing.scalar_one_or_none()
            
            if race:
                # 업데이트
                race.raw_data = data
                race.updated_at = datetime.utcnow()
                race.status = "collected"
            else:
                # 신규 생성
                race = Race(
                    race_date=data["race_date"],
                    meet=data["meet"],
                    race_no=data["race_no"],
                    raw_data=data,
                    status="collected"
                )
                db.add(race)
            
            await db.commit()
            
        except Exception as e:
            logger.error("Failed to save race data", error=str(e))
            await db.rollback()
            raise
    
    async def preprocess_race_data(
        self,
        race_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        경주 데이터 전처리
        
        Args:
            race_id: 경주 ID
            db: 데이터베이스 세션
            
        Returns:
            전처리된 데이터
        """
        try:
            # 경주 데이터 로드
            result = await db.execute(
                select(Race).where(Race.id == race_id)
            )
            race = result.scalar_one_or_none()
            
            if not race:
                raise ValueError(f"Race not found: {race_id}")
            
            raw_data = race.raw_data
            
            # 전처리 수행
            preprocessed = await self._preprocess_data(raw_data)
            
            # 저장
            race.preprocessed_data = preprocessed
            race.status = "preprocessed"
            race.updated_at = datetime.utcnow()
            
            await db.commit()
            
            return preprocessed
            
        except Exception as e:
            logger.error("Preprocessing failed", race_id=race_id, error=str(e))
            await db.rollback()
            raise
    
    async def _preprocess_data(
        self,
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """데이터 전처리 로직"""
        try:
            horses = raw_data.get("horses", [])
            
            # 기권마 필터링
            active_horses = []
            for h in horses:
                try:
                    win_odds = float(h.get("win_odds", 0))
                    if win_odds > 0:
                        active_horses.append(h)
                except (ValueError, TypeError):
                    # Skip horses with invalid win_odds
                    pass
            
            # 기본 통계 계산
            if active_horses:
                df = pd.DataFrame(active_horses)
                
                # 평균 계산
                avg_weight = df["weight"].mean() if "weight" in df else 0
                avg_rating = df["rating"].mean() if "rating" in df else 0
                avg_win_odds = df["win_odds"].mean() if "win_odds" in df else 0
                
                # 각 마필에 대한 상대적 지표 계산
                for horse in active_horses:
                    if avg_weight > 0:
                        try:
                            horse["weight_ratio"] = float(horse.get("weight", 0)) / avg_weight
                        except (ValueError, TypeError):
                            horse["weight_ratio"] = 0
                    if avg_rating > 0:
                        try:
                            horse["rating_ratio"] = float(horse.get("rating", 0)) / avg_rating
                        except (ValueError, TypeError):
                            horse["rating_ratio"] = 0
                    if avg_win_odds > 0:
                        try:
                            horse["odds_ratio"] = float(horse.get("win_odds", 0)) / avg_win_odds
                        except (ValueError, TypeError):
                            horse["odds_ratio"] = 0
            
            preprocessed = {
                **raw_data,
                "horses": active_horses,
                "excluded_horses": len(horses) - len(active_horses),
                "preprocessing_timestamp": datetime.utcnow().isoformat(),
                "statistics": {
                    "avg_weight": avg_weight if 'avg_weight' in locals() else 0,
                    "avg_rating": avg_rating if 'avg_rating' in locals() else 0,
                    "avg_win_odds": avg_win_odds if 'avg_win_odds' in locals() else 0
                }
            }
            
            return preprocessed
            
        except Exception as e:
            logger.error("Preprocessing logic failed", error=str(e))
            raise
    
    async def enrich_race_data(
        self,
        race_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        경주 데이터 강화
        
        Args:
            race_id: 경주 ID
            db: 데이터베이스 세션
            
        Returns:
            강화된 데이터
        """
        try:
            # 경주 데이터 로드
            result = await db.execute(
                select(Race).where(Race.id == race_id)
            )
            race = result.scalar_one_or_none()
            
            if not race:
                raise ValueError(f"Race not found: {race_id}")
            
            preprocessed_data = race.preprocessed_data or race.raw_data
            
            # 강화 수행
            enriched = await self._enrich_data(preprocessed_data, db)
            
            # 저장
            race.enriched_data = enriched
            race.status = "enriched"
            race.updated_at = datetime.utcnow()
            
            await db.commit()
            
            return enriched
            
        except Exception as e:
            logger.error("Enrichment failed", race_id=race_id, error=str(e))
            await db.rollback()
            raise
    
    async def _enrich_data(
        self,
        data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """데이터 강화 로직"""
        try:
            horses = data.get("horses", [])
            race_date = data.get("race_date")
            meet = data.get("meet")
            
            # 각 마필에 대한 과거 성적 조회
            for horse in horses:
                horse_no = horse.get("horse_no")
                
                # 과거 3개월 성적 조회
                past_performances = await self._get_horse_past_performances(
                    horse_no, race_date, db
                )
                
                # 성적 통계 계산
                if past_performances:
                    horse["past_stats"] = self._calculate_performance_stats(
                        past_performances
                    )
                else:
                    horse["past_stats"] = self._get_default_stats()
                
                # 기수/조교사 통계
                jockey_no = horse.get("jockey_no")
                trainer_no = horse.get("trainer_no")
                
                if jockey_no:
                    horse["jockey_stats"] = await self._get_jockey_stats(
                        jockey_no, race_date, db
                    )
                
                if trainer_no:
                    horse["trainer_stats"] = await self._get_trainer_stats(
                        trainer_no, race_date, db
                    )
            
            # 날씨 영향 분석
            weather = data.get("weather", {})
            weather_impact = self._analyze_weather_impact(weather)
            
            enriched = {
                **data,
                "horses": horses,
                "weather_impact": weather_impact,
                "enrichment_timestamp": datetime.utcnow().isoformat()
            }
            
            return enriched
            
        except Exception as e:
            logger.error("Enrichment logic failed", error=str(e))
            raise
    
    async def _get_horse_past_performances(
        self,
        horse_no: str,
        race_date: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """마필 과거 성적 조회"""
        # 실제 구현에서는 데이터베이스에서 조회
        # 여기서는 간단한 예시
        return []
    
    def _calculate_performance_stats(
        self,
        performances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """성적 통계 계산"""
        df = pd.DataFrame(performances)
        
        return {
            "total_races": len(performances),
            "wins": len(df[df["position"] == 1]),
            "win_rate": len(df[df["position"] == 1]) / len(df) if len(df) > 0 else 0,
            "avg_position": df["position"].mean() if "position" in df else 0,
            "recent_form": self._calculate_recent_form(df)
        }
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """기본 통계값"""
        return {
            "total_races": 0,
            "wins": 0,
            "win_rate": 0,
            "avg_position": 0,
            "recent_form": 0
        }
    
    def _calculate_recent_form(self, df: pd.DataFrame) -> float:
        """최근 폼 계산"""
        if len(df) == 0:
            return 0
        
        # 최근 5경기 가중치 적용
        recent = df.head(5)
        weights = [5, 4, 3, 2, 1][:len(recent)]
        
        form_score = 0
        for i, (_, race) in enumerate(recent.iterrows()):
            position = race.get("position", 10)
            score = max(0, 11 - position) * weights[i]
            form_score += score
        
        max_score = sum(weights) * 10
        return form_score / max_score if max_score > 0 else 0
    
    async def _get_jockey_stats(
        self,
        jockey_no: str,
        race_date: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """기수 통계 조회"""
        # 실제 구현에서는 데이터베이스에서 조회
        return {
            "recent_win_rate": 0.15,
            "meet_win_rate": 0.12,
            "total_wins": 150
        }
    
    async def _get_trainer_stats(
        self,
        trainer_no: str,
        race_date: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """조교사 통계 조회"""
        # 실제 구현에서는 데이터베이스에서 조회
        return {
            "recent_win_rate": 0.18,
            "meet_win_rate": 0.16,
            "total_wins": 200
        }
    
    def _analyze_weather_impact(
        self,
        weather: Dict[str, Any]
    ) -> Dict[str, Any]:
        """날씨 영향 분석"""
        track_condition = weather.get("track_condition", "good")
        
        impact = {
            "track_speed_factor": 1.0,
            "stamina_importance": 1.0,
            "weight_impact": 1.0
        }
        
        if track_condition in ["heavy", "soft"]:
            impact["track_speed_factor"] = 0.95
            impact["stamina_importance"] = 1.2
            impact["weight_impact"] = 1.1
        elif track_condition == "firm":
            impact["track_speed_factor"] = 1.05
            impact["stamina_importance"] = 0.9
        
        return impact
    
    async def collect_batch_races(
        self,
        race_date: str,
        meet: int,
        race_numbers: List[int],
        db: AsyncSession
    ) -> Dict[int, Dict[str, Any]]:
        """
        여러 경주 일괄 수집
        
        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_numbers: 경주 번호 리스트
            db: 데이터베이스 세션
            
        Returns:
            경주 번호별 수집 결과
        """
        results = {}
        
        for race_no in race_numbers:
            try:
                result = await self.collect_race_data(
                    race_date, meet, race_no, db
                )
                results[race_no] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(
                    "Batch collection failed for race",
                    race_no=race_no,
                    error=str(e)
                )
                results[race_no] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results