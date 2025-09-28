"""
Data Processing Pipeline
경주 데이터 수집부터 검증까지의 전체 처리 파이프라인
"""

from sqlalchemy.ext.asyncio import AsyncSession

from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService

from .base import Pipeline, PipelineBuilder, PipelineContext
from .stages import (
    CollectionStage,
    EnrichmentStage,
    PreprocessingStage,
    ValidationStage,
)


class DataProcessingPipeline:
    """
    데이터 처리 파이프라인 팩토리 클래스
    경주 데이터의 전체 처리 프로세스를 관리
    """

    @staticmethod
    def create_standard_pipeline(
        kra_api_service: KRAAPIService,
        db_session: AsyncSession,
        min_horses: int = 5,
        min_quality_score: float = 0.7,
    ) -> Pipeline:
        """
        표준 데이터 처리 파이프라인 생성

        Args:
            kra_api_service: KRA API 서비스
            db_session: 데이터베이스 세션
            min_horses: 최소 마필 수
            min_quality_score: 최소 품질 점수

        Returns:
            구성된 파이프라인
        """
        collection_service = CollectionService(kra_api_service)

        pipeline = (
            PipelineBuilder("standard_data_processing")
            .add_stage(CollectionStage(kra_api_service, db_session))
            .add_stage(PreprocessingStage())
            .add_stage(EnrichmentStage(collection_service, db_session))
            .add_stage(ValidationStage(min_horses, min_quality_score))
            .build()
        )

        return pipeline

    @staticmethod
    def create_collection_only_pipeline(
        kra_api_service: KRAAPIService, db_session: AsyncSession
    ) -> Pipeline:
        """
        수집 전용 파이프라인 생성 (빠른 수집용)

        Args:
            kra_api_service: KRA API 서비스
            db_session: 데이터베이스 세션

        Returns:
            수집 전용 파이프라인
        """
        pipeline = (
            PipelineBuilder("collection_only")
            .add_stage(CollectionStage(kra_api_service, db_session))
            .add_stage(PreprocessingStage())
            .build()
        )

        return pipeline

    @staticmethod
    def create_enrichment_pipeline(
        kra_api_service: KRAAPIService,
        db_session: AsyncSession,
        min_quality_score: float = 0.8,
    ) -> Pipeline:
        """
        보강 전용 파이프라인 생성 (이미 수집된 데이터의 보강용)

        Args:
            kra_api_service: KRA API 서비스
            db_session: 데이터베이스 세션
            min_quality_score: 최소 품질 점수

        Returns:
            보강 전용 파이프라인
        """
        collection_service = CollectionService(kra_api_service)

        pipeline = (
            PipelineBuilder("enrichment_only")
            .add_stage(EnrichmentStage(collection_service, db_session))
            .add_stage(
                ValidationStage(min_horses=1, min_quality_score=min_quality_score)
            )
            .build()
        )

        return pipeline

    @staticmethod
    async def process_race_data(
        race_date: str,
        meet: int,
        race_number: int,
        kra_api_service: KRAAPIService,
        db_session: AsyncSession,
        pipeline_type: str = "standard",
        **kwargs,
    ) -> PipelineContext:
        """
        경주 데이터 처리 실행

        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드
            race_number: 경주 번호
            kra_api_service: KRA API 서비스
            db_session: 데이터베이스 세션
            pipeline_type: 파이프라인 타입 ('standard', 'collection_only', 'enrichment_only')
            **kwargs: 추가 파라미터

        Returns:
            완료된 파이프라인 컨텍스트

        Raises:
            ValueError: 잘못된 파이프라인 타입
            PipelineExecutionError: 파이프라인 실행 실패
        """
        # 컨텍스트 생성
        context = PipelineContext(
            race_date=race_date, meet=meet, race_number=race_number
        )

        # 파이프라인 타입에 따른 파이프라인 생성
        if pipeline_type == "standard":
            pipeline = DataProcessingPipeline.create_standard_pipeline(
                kra_api_service, db_session, **kwargs
            )
        elif pipeline_type == "collection_only":
            pipeline = DataProcessingPipeline.create_collection_only_pipeline(
                kra_api_service, db_session
            )
        elif pipeline_type == "enrichment_only":
            pipeline = DataProcessingPipeline.create_enrichment_pipeline(
                kra_api_service, db_session, **kwargs
            )
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")

        # 파이프라인 실행
        result_context = await pipeline.execute(context)
        return result_context


class PipelineOrchestrator:
    """
    파이프라인 오케스트레이터
    여러 경주의 배치 처리 및 파이프라인 관리
    """

    def __init__(self, kra_api_service: KRAAPIService, db_session: AsyncSession):
        self.kra_api_service = kra_api_service
        self.db_session = db_session

    async def process_race_batch(
        self,
        race_requests: list[dict],
        pipeline_type: str = "standard",
        max_concurrent: int = 3,
        **kwargs,
    ) -> list[PipelineContext]:
        """
        여러 경주 배치 처리

        Args:
            race_requests: 경주 요청 목록 [{"race_date": "20240101", "meet": 1, "race_number": 1}, ...]
            pipeline_type: 파이프라인 타입
            max_concurrent: 최대 동시 실행 수
            **kwargs: 추가 파라미터

        Returns:
            처리 결과 목록
        """
        import asyncio

        async def process_single_race(race_request: dict) -> PipelineContext:
            """단일 경주 처리"""
            try:
                return await DataProcessingPipeline.process_race_data(
                    race_date=race_request["race_date"],
                    meet=race_request["meet"],
                    race_number=race_request["race_number"],
                    kra_api_service=self.kra_api_service,
                    db_session=self.db_session,
                    pipeline_type=pipeline_type,
                    **kwargs,
                )
            except Exception as e:
                # 실패한 경주의 경우 실패 정보가 포함된 컨텍스트 반환
                context = PipelineContext(
                    race_date=race_request["race_date"],
                    meet=race_request["meet"],
                    race_number=race_request["race_number"],
                )
                context.metadata["error"] = str(e)
                context.metadata["failed"] = True
                return context

        # 세마포어를 사용한 동시 실행 제한
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(race_request: dict) -> PipelineContext:
            async with semaphore:
                return await process_single_race(race_request)

        # 모든 경주 병렬 처리
        tasks = [process_with_semaphore(request) for request in race_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 예외가 발생한 경우 실패 컨텍스트 생성
                race_request = race_requests[i]
                context = PipelineContext(
                    race_date=race_request["race_date"],
                    meet=race_request["meet"],
                    race_number=race_request["race_number"],
                )
                context.metadata["error"] = str(result)
                context.metadata["failed"] = True
                processed_results.append(context)
            else:
                processed_results.append(result)

        return processed_results

    async def process_date_range(
        self,
        start_date: str,
        end_date: str,
        meets: list[int],
        race_numbers: list[int],
        pipeline_type: str = "standard",
        **kwargs,
    ) -> list[PipelineContext]:
        """
        날짜 범위의 경주 처리

        Args:
            start_date: 시작 날짜 (YYYYMMDD)
            end_date: 종료 날짜 (YYYYMMDD)
            meets: 경마장 목록
            race_numbers: 경주 번호 목록
            pipeline_type: 파이프라인 타입
            **kwargs: 추가 파라미터

        Returns:
            처리 결과 목록
        """
        from datetime import datetime, timedelta

        # 날짜 범위 생성
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")

        race_requests = []
        current_date = start

        while current_date <= end:
            date_str = current_date.strftime("%Y%m%d")
            for meet in meets:
                for race_number in race_numbers:
                    race_requests.append(
                        {
                            "race_date": date_str,
                            "meet": meet,
                            "race_number": race_number,
                        }
                    )
            current_date += timedelta(days=1)

        return await self.process_race_batch(race_requests, pipeline_type, **kwargs)

    def get_pipeline_status_summary(self, contexts: list[PipelineContext]) -> dict:
        """
        파이프라인 실행 결과 요약

        Args:
            contexts: 파이프라인 컨텍스트 목록

        Returns:
            실행 결과 요약
        """
        total = len(contexts)
        successful = sum(1 for ctx in contexts if not ctx.metadata.get("failed", False))
        failed = total - successful

        # 단계별 성공률 계산
        stage_stats = {}
        for context in contexts:
            for stage_name, result in context.stage_results.items():
                if stage_name not in stage_stats:
                    stage_stats[stage_name] = {"success": 0, "failed": 0, "total": 0}

                stage_stats[stage_name]["total"] += 1
                if result.is_success():
                    stage_stats[stage_name]["success"] += 1
                else:
                    stage_stats[stage_name]["failed"] += 1

        # 평균 실행 시간 계산
        execution_times = [
            ctx.get_execution_time_ms()
            for ctx in contexts
            if ctx.get_execution_time_ms() is not None
        ]
        avg_execution_time = (
            sum(execution_times) / len(execution_times) if execution_times else None
        )

        return {
            "total_races": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "stage_statistics": stage_stats,
            "average_execution_time_ms": avg_execution_time,
            "total_execution_time_ms": (
                sum(execution_times) if execution_times else None
            ),
        }
