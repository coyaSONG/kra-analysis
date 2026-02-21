"""
DB 데이터 → 평가 스크립트 호환 포맷 변환 어댑터

DB basic_data 구조:
  race_info: {response: {body: {items: {item: [camelCase 기본 데이터]}}}}
  horses: [{chul_no, hr_name, ..., hrDetail: {snake_case}, jkDetail, trDetail}]

평가 스크립트 기대 포맷:
  {response: {body: {items: {item: [camelCase + hrDetail/jkDetail/trDetail(camelCase)]}}}}
"""

from typing import Any


def _snake_to_camel(name: str) -> str:
    """snake_case → camelCase 변환"""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _convert_dict_keys_to_camel(d: dict[str, Any]) -> dict[str, Any]:
    """dict의 모든 키를 snake_case → camelCase로 변환"""
    result = {}
    for key, value in d.items():
        camel_key = _snake_to_camel(key)
        if isinstance(value, dict):
            result[camel_key] = _convert_dict_keys_to_camel(value)
        elif isinstance(value, list):
            result[camel_key] = [
                _convert_dict_keys_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[camel_key] = value
    return result


def convert_basic_data_to_enriched_format(basic_data: dict) -> dict | None:
    """DB basic_data를 평가 스크립트가 기대하는 enriched 포맷으로 변환

    Args:
        basic_data: DB races.basic_data 컬럼 값

    Returns:
        {response: {body: {items: {item: [...]}}}} 형태 또는 None
    """
    if not basic_data:
        return None

    race_info = basic_data.get("race_info")
    horses = basic_data.get("horses", [])

    if not race_info:
        return None

    # race_info에서 원본 camelCase items 추출
    try:
        items = race_info["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]
    except (KeyError, TypeError):
        return None

    if not items:
        return None

    # horses 배열에서 chul_no → detail 매핑 생성
    detail_map: dict[int, dict] = {}
    for horse in horses:
        chul_no = horse.get("chul_no")
        if chul_no is None:
            continue
        details = {}
        for detail_key in ("hrDetail", "jkDetail", "trDetail"):
            if detail_key in horse and horse[detail_key]:
                # detail 값의 snake_case 키 → camelCase 변환
                details[detail_key] = _convert_dict_keys_to_camel(horse[detail_key])
        detail_map[int(chul_no)] = details

    # 각 camelCase item에 detail 병합
    merged_items = []
    for item in items:
        merged = {**item}
        chul_no = item.get("chulNo")
        if chul_no is not None and int(chul_no) in detail_map:
            merged.update(detail_map[int(chul_no)])
        merged_items.append(merged)

    return {"response": {"body": {"items": {"item": merged_items}}}}
