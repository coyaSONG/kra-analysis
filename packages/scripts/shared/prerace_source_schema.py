"""출전표 확정 시점 공통 스키마와 원천 필드 매핑 명세.

이 모듈은 "예측 시점에 사용 가능한 정보만 허용"이라는 제약을 코드로 고정한다.
운영 파이프라인의 저장 구조(`basic_data`)를 기준으로 공통 스키마를 정의하고,
각 KRA 원천 API 필드가 어느 스키마 경로로 들어와야 하는지 선언한다.
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "prerace-source-v1"


@dataclass(frozen=True, slots=True)
class FieldMappingSpec:
    """원천 필드에서 공통 스키마로 들어오는 단일 매핑 규칙."""

    source_api: str
    source_field: str
    schema_path: str
    required: bool
    transform: str
    join_key: str | None = None


SOURCE_API_REGISTRY: dict[str, str] = {
    "API214_1": "경주 출전표 기본 행",
    "API72_2": "경주계획표",
    "API189_1": "경주로/날씨 정보",
    "API9_1": "출전취소 정보",
    "API8_2": "말 상세 정보",
    "API12_1": "기수 상세 정보",
    "API19_1": "조교사 상세 정보",
    "API11_1": "기수 성적 정보",
    "API14_1": "마주 정보",
    "API329": "조교 현황",
}

# 모든 경주에 대해 예측을 생성하려면 최소한 수집돼야 하는 소스
HARD_REQUIRED_SOURCE_APIS: tuple[str, ...] = (
    "API214_1",
    "API72_2",
    "API189_1",
    "API9_1",
)

# 성능 고도화에는 중요하지만, 일시 실패 시 빈 블록 허용 가능
SOFT_REQUIRED_SOURCE_APIS: tuple[str, ...] = (
    "API8_2",
    "API12_1",
    "API19_1",
    "API11_1",
    "API14_1",
    "API329",
)

# 수집 파이프라인이 원천 API 없이 생성하는 메타데이터
DERIVED_SCHEMA_PATHS: frozenset[str] = frozenset(
    {
        "schema_version",
        "date",
        "race_number",
        "collected_at",
        "status",
        "failed_horses",
    }
)

TOP_LEVEL_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "race_date",
    "race_no",
    "date",
    "meet",
    "race_number",
    "race_info",
    "race_plan",
    "track",
    "cancelled_horses",
    "horses",
    "collected_at",
    "status",
)

# 예측 불가 상태를 막기 위해 경주 스냅샷마다 반드시 채워져야 하는 최소 경로
REQUIRED_SCHEMA_PATHS: frozenset[str] = frozenset(
    {
        "race_date",
        "race_no",
        "meet",
        "race_info.response.body.items.item[]",
        "race_plan.rank",
        "race_plan.budam",
        "race_plan.rc_dist",
        "race_plan.age_cond",
        "track.weather",
        "track.track",
        "track.water_percent",
        "horses[].chul_no",
        "horses[].hr_no",
        "horses[].hr_name",
        "horses[].jk_no",
        "horses[].jk_name",
        "horses[].tr_no",
        "horses[].tr_name",
        "horses[].ow_no",
        "horses[].ow_name",
        "horses[].age",
        "horses[].sex",
        "horses[].name",
        "horses[].rank",
        "horses[].rating",
        "horses[].wg_budam",
        "horses[].wg_budam_bigo",
        "horses[].wg_hr",
        "horses[].win_odds",
        "horses[].plc_odds",
        "cancelled_horses[]",
    }
)

# 스키마에는 예약하지만, 원천 실패 시 null/빈 dict를 허용하는 확장 블록
OPTIONAL_SCHEMA_PATHS: frozenset[str] = frozenset(
    {
        "horses[].ilsu",
        "horses[].hr_tool",
        "horses[].hrDetail",
        "horses[].jkDetail",
        "horses[].trDetail",
        "horses[].jkStats",
        "horses[].owDetail",
        "horses[].training",
        "track.temperature",
        "track.humidity",
        "track.wind_direction",
        "track.wind_speed",
        "race_plan.sex_cond",
        "race_plan.sch_st_time",
        "race_plan.chaksun1",
        "race_plan.chaksun2",
        "race_plan.chaksun3",
        "race_plan.chaksun4",
        "race_plan.chaksun5",
    }
)

LEAKAGE_GUARD_RULES: tuple[str, ...] = (
    "`ord`, `rcTime`, 구간통과 순위/기록, 배당금/확정결과 등 사후 필드는 입력 스키마에 넣지 않는다.",
    "원천에 `rank`가 들어오면 저장 시에는 원문 유지 가능하지만, 모델 입력으로 내보낼 때는 `class_rank`로 rename 한다.",
    "`winOdds == 0` 출전마는 저장은 하되 모델 입력 구성 시 제외마로 취급한다.",
    "training API는 `hrNo`가 없으므로 현재 구현 기준 `hrName` 매칭을 사용하고 unmatched는 경고로 남긴다.",
)


SOURCE_FIELD_MAPPINGS: tuple[FieldMappingSpec, ...] = (
    FieldMappingSpec(
        source_api="API214_1",
        source_field="response.body.items.item[]",
        schema_path="race_info.response.body.items.item[]",
        required=True,
        transform="원본 camelCase 응답 envelope 전체를 보존한다.",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="rcDate",
        schema_path="race_date",
        required=True,
        transform="모든 item에서 동일해야 하며 YYYYMMDD 문자열로 고정한다.",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="rcNo",
        schema_path="race_no",
        required=True,
        transform="정수 경주번호로 저장하고 `race_number` 파생값 생성에 재사용한다.",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="meet",
        schema_path="meet",
        required=True,
        transform="정수 meet 코드를 top-level에 저장하고 원문 meet 문자열은 race_info에 남긴다.",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="chulNo",
        schema_path="horses[].chul_no",
        required=True,
        transform="출전번호 기준으로 말별 블록을 정렬/조인한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="hrNo",
        schema_path="horses[].hr_no",
        required=True,
        transform="문자열 식별자로 보존한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="hrName",
        schema_path="horses[].hr_name",
        required=True,
        transform="원문 한글명을 그대로 보존한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="jkNo",
        schema_path="horses[].jk_no",
        required=True,
        transform="기수 상세/성적 API 조인키로 재사용한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="jkName",
        schema_path="horses[].jk_name",
        required=True,
        transform="원문 이름을 그대로 보존한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="trNo",
        schema_path="horses[].tr_no",
        required=True,
        transform="조교사 상세 API 조인키로 재사용한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="trName",
        schema_path="horses[].tr_name",
        required=True,
        transform="원문 이름을 그대로 보존한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="owNo",
        schema_path="horses[].ow_no",
        required=True,
        transform="마주 정보 API 조인키로 사용한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="owName",
        schema_path="horses[].ow_name",
        required=True,
        transform="원문 이름을 그대로 보존한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="age",
        schema_path="horses[].age",
        required=True,
        transform="정수형 나이로 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="sex",
        schema_path="horses[].sex",
        required=True,
        transform="수/암/거 원문 enum을 그대로 유지한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="name",
        schema_path="horses[].name",
        required=True,
        transform="산지/국적 원문을 그대로 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="rank",
        schema_path="horses[].rank",
        required=True,
        transform="원본 저장은 `rank` 그대로, 모델 입력 변환 시 `class_rank`로 rename 한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="rating",
        schema_path="horses[].rating",
        required=True,
        transform="숫자형 레이팅으로 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="wgBudam",
        schema_path="horses[].wg_budam",
        required=True,
        transform="부담중량 숫자 필드로 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="wgBudamBigo",
        schema_path="horses[].wg_budam_bigo",
        required=True,
        transform="감량/할증 보조 표기 원문을 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="wgHr",
        schema_path="horses[].wg_hr",
        required=True,
        transform="마체중과 증감 문자열 원문을 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="winOdds",
        schema_path="horses[].win_odds",
        required=True,
        transform="0이면 제외마로 간주하되 원문 값은 유지한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="plcOdds",
        schema_path="horses[].plc_odds",
        required=True,
        transform="연승 배당률 숫자형으로 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="ilsu",
        schema_path="horses[].ilsu",
        required=False,
        transform="휴양일수 보조 피처로 사용한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API214_1",
        source_field="hrTool",
        schema_path="horses[].hr_tool",
        required=False,
        transform="마구 정보 원문 문자열을 저장한다.",
        join_key="chulNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="rank",
        schema_path="race_plan.rank",
        required=True,
        transform="`rcNo`가 대상 경주와 일치하는 item만 사용한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="budam",
        schema_path="race_plan.budam",
        required=True,
        transform="부담 조건 원문을 그대로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="rcDist",
        schema_path="race_plan.rc_dist",
        required=True,
        transform="미터 단위 거리 숫자값으로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="ageCond",
        schema_path="race_plan.age_cond",
        required=True,
        transform="연령 조건 원문을 그대로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="sexCond",
        schema_path="race_plan.sex_cond",
        required=False,
        transform="성별 조건 원문을 그대로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API72_2",
        source_field="schStTime",
        schema_path="race_plan.sch_st_time",
        required=False,
        transform="원문 숫자 또는 문자열 시각값을 그대로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API189_1",
        source_field="weather",
        schema_path="track.weather",
        required=True,
        transform="`rcNo`가 대상 경주와 일치하는 item만 사용한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API189_1",
        source_field="track",
        schema_path="track.track",
        required=True,
        transform="주로 상태 원문을 그대로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API189_1",
        source_field="waterPercent",
        schema_path="track.water_percent",
        required=True,
        transform="정수 수분율로 저장한다.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API9_1",
        source_field="*",
        schema_path="cancelled_horses[]",
        required=True,
        transform="`rcNo`가 대상 경주와 일치하는 전체 row를 snake_case로 저장한다. 없으면 빈 배열.",
        join_key="rcNo",
    ),
    FieldMappingSpec(
        source_api="API8_2",
        source_field="*",
        schema_path="horses[].hrDetail",
        required=False,
        transform="`hrNo`로 조인한 상세 row 전체를 snake_case 블록으로 저장한다.",
        join_key="hrNo",
    ),
    FieldMappingSpec(
        source_api="API12_1",
        source_field="*",
        schema_path="horses[].jkDetail",
        required=False,
        transform="`jkNo`로 조인한 상세 row 전체를 snake_case 블록으로 저장한다.",
        join_key="jkNo",
    ),
    FieldMappingSpec(
        source_api="API19_1",
        source_field="*",
        schema_path="horses[].trDetail",
        required=False,
        transform="`trNo`로 조인한 상세 row 전체를 snake_case 블록으로 저장한다.",
        join_key="trNo",
    ),
    FieldMappingSpec(
        source_api="API11_1",
        source_field="*",
        schema_path="horses[].jkStats",
        required=False,
        transform="`jkNo`로 조인한 성적 row 전체를 snake_case 블록으로 저장한다.",
        join_key="jkNo",
    ),
    FieldMappingSpec(
        source_api="API14_1",
        source_field="*",
        schema_path="horses[].owDetail",
        required=False,
        transform="`owNo`로 조인한 마주 row 전체를 snake_case 블록으로 저장한다.",
        join_key="owNo",
    ),
    FieldMappingSpec(
        source_api="API329",
        source_field="*",
        schema_path="horses[].training",
        required=False,
        transform="현재 구현 기준 `hrnm`/`hrName` 매칭으로 snake_case 블록 저장, 실패 시 빈 블록.",
        join_key="hrName",
    ),
)


def mappings_by_schema_path() -> dict[str, tuple[FieldMappingSpec, ...]]:
    """스키마 경로별 매핑 규칙 조회."""

    bucket: dict[str, list[FieldMappingSpec]] = {}
    for mapping in SOURCE_FIELD_MAPPINGS:
        bucket.setdefault(mapping.schema_path, []).append(mapping)
    return {key: tuple(value) for key, value in bucket.items()}


def required_mappings() -> tuple[FieldMappingSpec, ...]:
    """required=True 매핑만 반환."""

    return tuple(mapping for mapping in SOURCE_FIELD_MAPPINGS if mapping.required)
