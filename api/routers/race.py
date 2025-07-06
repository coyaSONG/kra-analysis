from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
import structlog
from infrastructure.supabase_client import get_supabase_client
from services.race_service import RaceService
from models.race_dto import (
    CollectRaceRequest,
    CollectRaceResponse,
    RaceData,
    RaceResult,
)


router = APIRouter()
logger = structlog.get_logger()


@router.post("/collect", response_model=CollectRaceResponse)
async def collect_races(
    request: CollectRaceRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase_client),
):
    """
    수집 작업을 시작합니다. 백그라운드에서 처리되며 작업 ID를 반환합니다.
    
    - **date**: YYYYMMDD 형식의 날짜
    - **meet**: 경마장 (1:서울, 2:제주, 3:부산경남)
    - **race_no**: 경주 번호 (선택, 없으면 전체)
    """
    try:
        race_service = RaceService(supabase)
        job_id = await race_service.create_collection_job(request)
        
        # 백그라운드 작업 추가
        background_tasks.add_task(
            race_service.process_collection,
            job_id,
            request.date,
            request.meet,
            request.race_no,
        )
        
        return CollectRaceResponse(
            job_id=job_id,
            status="queued",
            message=f"Collection job created for {request.date}"
        )
        
    except Exception as e:
        logger.error("Failed to create collection job", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich/{race_id}")
async def enrich_race(
    race_id: str,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase_client),
):
    """
    특정 경주의 데이터를 보강합니다 (말, 기수, 조교사 상세 정보).
    """
    try:
        race_service = RaceService(supabase)
        
        # 경주 존재 확인
        race = await race_service.get_race(race_id)
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        
        # 백그라운드 작업 추가
        background_tasks.add_task(
            race_service.enrich_race_data,
            race_id,
        )
        
        return {
            "race_id": race_id,
            "status": "enrichment_started",
            "message": "Enrichment process started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start enrichment", race_id=race_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{date}/{meet}/{race_no}", response_model=Optional[RaceResult])
async def get_race_result(
    date: str,
    meet: int,
    race_no: int,
    supabase=Depends(get_supabase_client),
):
    """
    특정 경주의 결과를 조회합니다.
    
    Returns:
        1-2-3위 말번호 리스트 [10, 3, 5]
    """
    try:
        race_service = RaceService(supabase)
        result = await race_service.get_race_result(date, meet, race_no)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Race result not found for {date} meet {meet} race {race_no}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get race result", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{date}", response_model=List[RaceData])
async def list_races_by_date(
    date: str,
    meet: Optional[int] = None,
    supabase=Depends(get_supabase_client),
):
    """
    특정 날짜의 경주 목록을 조회합니다.
    """
    try:
        race_service = RaceService(supabase)
        races = await race_service.list_races_by_date(date, meet)
        
        return races
        
    except Exception as e:
        logger.error("Failed to list races", date=date, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{race_id}/status")
async def get_race_status(
    race_id: str,
    supabase=Depends(get_supabase_client),
):
    """
    특정 경주의 데이터 수집 상태를 확인합니다.
    """
    try:
        race_service = RaceService(supabase)
        status = await race_service.get_race_status(race_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Race not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get race status", race_id=race_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))