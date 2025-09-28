"""
KRA API 응답 어댑터
KRA API의 응답 구조를 정규화하고 비즈니스 로직에서 분리
"""

from typing import Any, Dict, List, Optional, Union
import structlog

logger = structlog.get_logger()


class KRAResponseAdapter:
    """KRA API 응답을 정규화된 형태로 변환하는 어댑터"""

    @staticmethod
    def extract_items(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        KRA API 응답에서 items 추출 및 정규화

        Args:
            api_response: KRA API 원본 응답

        Returns:
            정규화된 아이템 리스트
        """
        if not api_response:
            return []

        try:
            # KRA API 표준 응답 구조: response.body.items.item
            if "response" not in api_response:
                logger.warning("KRA API response missing 'response' field")
                return []

            response_body = api_response["response"]
            if "body" not in response_body:
                logger.warning("KRA API response missing 'body' field")
                return []

            body = response_body["body"]
            if not body or "items" not in body:
                logger.warning("KRA API response missing 'items' field")
                return []

            items = body["items"]
            if not items or "item" not in items:
                logger.debug("KRA API response has no items")
                return []

            raw_items = items["item"]

            # 단일 아이템을 리스트로 정규화
            if not isinstance(raw_items, list):
                raw_items = [raw_items]

            return raw_items

        except (KeyError, TypeError) as e:
            logger.error(
                "Failed to extract items from KRA API response",
                error=str(e),
                response_keys=list(api_response.keys()) if isinstance(api_response, dict) else "not_dict"
            )
            return []

    @staticmethod
    def extract_single_item(api_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        KRA API 응답에서 단일 아이템 추출

        Args:
            api_response: KRA API 원본 응답

        Returns:
            첫 번째 아이템 또는 None
        """
        items = KRAResponseAdapter.extract_items(api_response)
        return items[0] if items else None

    @staticmethod
    def normalize_race_info(api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        경주 정보 응답 정규화

        Args:
            api_response: KRA API 경주 정보 응답

        Returns:
            정규화된 경주 정보
        """
        horses = KRAResponseAdapter.extract_items(api_response)

        return {
            "horses": horses,
            "horse_count": len(horses),
            "has_data": len(horses) > 0
        }

    @staticmethod
    def normalize_horse_info(api_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        마필 정보 응답 정규화

        Args:
            api_response: KRA API 마필 정보 응답

        Returns:
            정규화된 마필 정보 또는 None
        """
        horse_data = KRAResponseAdapter.extract_single_item(api_response)

        if not horse_data:
            return None

        return {
            "hr_no": horse_data.get("hrNo"),
            "hr_name": horse_data.get("hrName"),
            "win_rate": KRAResponseAdapter._safe_float(horse_data.get("win_rate_t")),
            "place_rate": KRAResponseAdapter._safe_float(horse_data.get("place_rate_t")),
            "recent_form": horse_data.get("recent_form"),
            "raw_data": horse_data  # 원본 데이터 보존
        }

    @staticmethod
    def normalize_jockey_info(api_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        기수 정보 응답 정규화

        Args:
            api_response: KRA API 기수 정보 응답

        Returns:
            정규화된 기수 정보 또는 None
        """
        jockey_data = KRAResponseAdapter.extract_single_item(api_response)

        if not jockey_data:
            return None

        return {
            "jk_no": jockey_data.get("jkNo"),
            "jk_name": jockey_data.get("jkName"),
            "win_rate": KRAResponseAdapter._safe_float(jockey_data.get("win_rate_t")),
            "race_count": KRAResponseAdapter._safe_int(jockey_data.get("rc_cnt_t")),
            "win_count": KRAResponseAdapter._safe_int(jockey_data.get("win_cnt_t")),
            "place_count": KRAResponseAdapter._safe_int(jockey_data.get("place_cnt_t")),
            "raw_data": jockey_data  # 원본 데이터 보존
        }

    @staticmethod
    def normalize_trainer_info(api_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        조교사 정보 응답 정규화

        Args:
            api_response: KRA API 조교사 정보 응답

        Returns:
            정규화된 조교사 정보 또는 None
        """
        trainer_data = KRAResponseAdapter.extract_single_item(api_response)

        if not trainer_data:
            return None

        return {
            "tr_no": trainer_data.get("trNo"),
            "tr_name": trainer_data.get("trName"),
            "win_rate": KRAResponseAdapter._safe_float(trainer_data.get("win_rate_t")),
            "race_count": KRAResponseAdapter._safe_int(trainer_data.get("rc_cnt_t")),
            "win_count": KRAResponseAdapter._safe_int(trainer_data.get("win_cnt_t")),
            "place_count": KRAResponseAdapter._safe_int(trainer_data.get("place_cnt_t")),
            "raw_data": trainer_data  # 원본 데이터 보존
        }

    @staticmethod
    def is_successful_response(api_response: Dict[str, Any]) -> bool:
        """
        KRA API 응답이 성공적인지 확인

        Args:
            api_response: KRA API 응답

        Returns:
            성공 여부
        """
        if not api_response:
            return False

        # 응답 구조 검증
        if "response" not in api_response:
            return False

        response = api_response["response"]

        # 에러 코드 확인 (KRA API 특성에 따라 조정 필요)
        if "header" in response:
            header = response["header"]
            result_code = header.get("resultCode", "")
            if result_code and result_code != "00":  # 00이 성공 코드라고 가정
                return False

        return True

    @staticmethod
    def get_error_message(api_response: Dict[str, Any]) -> str:
        """
        KRA API 응답에서 에러 메시지 추출

        Args:
            api_response: KRA API 응답

        Returns:
            에러 메시지
        """
        if not api_response:
            return "Empty API response"

        try:
            if "response" in api_response and "header" in api_response["response"]:
                header = api_response["response"]["header"]
                return header.get("resultMessage", "Unknown error")
        except (KeyError, TypeError):
            pass

        return "Failed to parse error message"

    @staticmethod
    def _safe_float(value: Any) -> float:
        """안전한 float 변환"""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        """안전한 int 변환"""
        if value is None or value == "":
            return 0
        try:
            return int(float(value))  # "12.0" 같은 경우를 위해 float를 거침
        except (ValueError, TypeError):
            return 0