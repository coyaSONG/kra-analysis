"""피처 생성·조인 원천의 출전표 확정 시점 시간 메타데이터 계약."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.prerace_field_metadata_schema import (
    AVAILABILITY_STAGES,
    OPERATIONAL_STATUSES,
    TRAIN_INFERENCE_FLAGS,
)

CONTRACT_VERSION = "feature-source-timing-contract-v1"
CANONICAL_STORAGE_RELATIVE_PATH = Path(
    "data/contracts/feature_source_timing_contract_v1.csv"
)
CANONICAL_STORAGE_FORMAT = "csv"
CANONICAL_STORAGE_ENCODING = "utf-8"
ROW_PRIMARY_KEY: tuple[str, ...] = ("source_block_id",)

SOURCE_SYSTEMS: tuple[str, ...] = (
    "KRA_API",
    "POSTGRES",
    "INTERNAL_DERIVED",
)

SOURCE_GRAINS: tuple[str, ...] = (
    "race",
    "race_entry",
    "horse",
    "jockey",
    "trainer",
    "owner",
    "race_odds_row",
    "prediction_row",
)

JOIN_SCOPES: tuple[str, ...] = (
    "self_materialized",
    "race_key",
    "horse_id",
    "jockey_id",
    "trainer_id",
    "owner_id",
    "horse_name_fallback",
    "same_race_aggregate",
    "historical_lookup",
    "postrace_feedback",
)

AS_OF_REQUIREMENTS: tuple[str, ...] = (
    "DIRECT_PRE_RACE",
    "PRE_CUTOFF_SNAPSHOT",
    "STORED_AS_OF_SNAPSHOT",
    "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
    "TIMING_UNVERIFIED",
    "POSTRACE_ONLY",
)


@dataclass(frozen=True, slots=True)
class ContractColumnSpec:
    name: str
    required: bool
    description: str


COLUMN_SPECS: tuple[ContractColumnSpec, ...] = (
    ContractColumnSpec(
        name="contract_version",
        required=True,
        description="계약 버전. 현재 값은 feature-source-timing-contract-v1.",
    ),
    ContractColumnSpec(
        name="source_block_id",
        required=True,
        description="피처 원천 블록 식별자.",
    ),
    ContractColumnSpec(
        name="source_system",
        required=True,
        description="KRA_API, POSTGRES, INTERNAL_DERIVED 중 하나.",
    ),
    ContractColumnSpec(
        name="source_object",
        required=True,
        description="원천 API/테이블/파생 블록 이름.",
    ),
    ContractColumnSpec(
        name="storage_path",
        required=True,
        description="현재 저장소에서 materialize 되는 canonical 경로.",
    ),
    ContractColumnSpec(
        name="grain",
        required=True,
        description="원천 블록의 grain.",
    ),
    ContractColumnSpec(
        name="source_columns",
        required=True,
        description="실제 피처 생성·조인에 쓰는 원천 컬럼 목록. | 구분자를 사용한다.",
    ),
    ContractColumnSpec(
        name="join_keys",
        required=True,
        description="조인 또는 집계 anchor key 설명.",
    ),
    ContractColumnSpec(
        name="join_scope",
        required=True,
        description="조인 방식 분류.",
    ),
    ContractColumnSpec(
        name="output_fields",
        required=True,
        description="이 블록이 직접 책임지는 output field 목록. | 구분자를 사용한다.",
    ),
    ContractColumnSpec(
        name="availability_stage",
        required=True,
        description="L-1, L0, L0 snapshot, ?, L+1 중 하나.",
    ),
    ContractColumnSpec(
        name="as_of_requirement",
        required=True,
        description="출전표 확정 시점 이전 사용을 위해 필요한 시간 조건.",
    ),
    ContractColumnSpec(
        name="late_update_rule",
        required=True,
        description="cutoff 이후 정정/재조회가 발생했을 때의 처리 규칙.",
    ),
    ContractColumnSpec(
        name="train_inference_flag",
        required=True,
        description="학습/추론 허용 플래그.",
    ),
    ContractColumnSpec(
        name="operational_status",
        required=True,
        description="허용/조건부 허용/보류/금지/메타 전용 등 운영 상태.",
    ),
    ContractColumnSpec(
        name="evidence_refs",
        required=True,
        description="근거 문서/코드 목록. | 구분자를 사용한다.",
    ),
    ContractColumnSpec(
        name="notes",
        required=False,
        description="보충 메모.",
    ),
)

REQUIRED_COLUMNS: tuple[str, ...] = tuple(
    column.name for column in COLUMN_SPECS if column.required
)
OPTIONAL_COLUMNS: tuple[str, ...] = tuple(
    column.name for column in COLUMN_SPECS if not column.required
)
ALL_COLUMNS: tuple[str, ...] = tuple(column.name for column in COLUMN_SPECS)


def csv_header() -> str:
    return ",".join(ALL_COLUMNS)


@dataclass(frozen=True, slots=True)
class FeatureSourceTimingRow:
    source_block_id: str
    source_system: str
    source_object: str
    storage_path: str
    grain: str
    source_columns: tuple[str, ...]
    join_keys: str
    join_scope: str
    output_fields: tuple[str, ...]
    availability_stage: str
    as_of_requirement: str
    late_update_rule: str
    train_inference_flag: str
    operational_status: str
    evidence_refs: tuple[str, ...]
    notes: str = ""

    def __post_init__(self) -> None:
        if self.source_system not in SOURCE_SYSTEMS:
            raise ValueError(f"unsupported source_system: {self.source_system}")
        if self.grain not in SOURCE_GRAINS:
            raise ValueError(f"unsupported grain: {self.grain}")
        if self.join_scope not in JOIN_SCOPES:
            raise ValueError(f"unsupported join_scope: {self.join_scope}")
        if self.availability_stage not in AVAILABILITY_STAGES:
            raise ValueError(
                f"unsupported availability_stage: {self.availability_stage}"
            )
        if self.as_of_requirement not in AS_OF_REQUIREMENTS:
            raise ValueError(f"unsupported as_of_requirement: {self.as_of_requirement}")
        if self.train_inference_flag not in TRAIN_INFERENCE_FLAGS:
            raise ValueError(
                f"unsupported train_inference_flag: {self.train_inference_flag}"
            )
        if self.operational_status not in OPERATIONAL_STATUSES:
            raise ValueError(
                f"unsupported operational_status: {self.operational_status}"
            )

    def to_csv_row(self) -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "source_block_id": self.source_block_id,
            "source_system": self.source_system,
            "source_object": self.source_object,
            "storage_path": self.storage_path,
            "grain": self.grain,
            "source_columns": "|".join(self.source_columns),
            "join_keys": self.join_keys,
            "join_scope": self.join_scope,
            "output_fields": "|".join(self.output_fields),
            "availability_stage": self.availability_stage,
            "as_of_requirement": self.as_of_requirement,
            "late_update_rule": self.late_update_rule,
            "train_inference_flag": self.train_inference_flag,
            "operational_status": self.operational_status,
            "evidence_refs": "|".join(self.evidence_refs),
            "notes": self.notes,
        }

    def covers_output(self, output_field: str) -> bool:
        return output_field in self.output_fields


def _row(
    *,
    source_block_id: str,
    source_system: str,
    source_object: str,
    storage_path: str,
    grain: str,
    source_columns: tuple[str, ...],
    join_keys: str,
    join_scope: str,
    output_fields: tuple[str, ...],
    availability_stage: str,
    as_of_requirement: str,
    late_update_rule: str,
    train_inference_flag: str,
    operational_status: str,
    evidence_refs: tuple[str, ...],
    notes: str = "",
) -> FeatureSourceTimingRow:
    return FeatureSourceTimingRow(
        source_block_id=source_block_id,
        source_system=source_system,
        source_object=source_object,
        storage_path=storage_path,
        grain=grain,
        source_columns=source_columns,
        join_keys=join_keys,
        join_scope=join_scope,
        output_fields=output_fields,
        availability_stage=availability_stage,
        as_of_requirement=as_of_requirement,
        late_update_rule=late_update_rule,
        train_inference_flag=train_inference_flag,
        operational_status=operational_status,
        evidence_refs=evidence_refs,
        notes=notes,
    )


_RULE_REFS = (
    "docs/holdout-entry-finalization-rule.md",
    "docs/prerace-data-whitelist-blacklist-policy.md",
    "docs/table-column-availability-map.md",
)
_FEATURE_REFS = (
    "packages/scripts/feature_engineering.py",
    "packages/scripts/autoresearch/research_clean.py",
    "data/contracts/prediction_input_field_registry_v1.csv",
)
_API_PIPELINE_REFS = (
    "apps/api/services/race_processing_workflow.py",
    "apps/api/services/collection_service.py",
    "apps/api/services/kra_api_service.py",
)
_DB_REFS = (
    "packages/scripts/shared/db_client.py",
    "packages/scripts/evaluation/data_loading.py",
)

FEATURE_SOURCE_TIMING_ROWS: tuple[FeatureSourceTimingRow, ...] = (
    _row(
        source_block_id="entry_card_core",
        source_system="KRA_API",
        source_object="API214_1.response.body.items.item[]",
        storage_path="races.basic_data.horses[]",
        grain="race_entry",
        source_columns=(
            "chulNo",
            "hrNo",
            "hrName",
            "jkNo",
            "jkName",
            "trNo",
            "trName",
            "owNo",
            "owName",
            "age",
            "sex",
            "rank",
            "rating",
            "wgBudam",
            "wgBudamBigo",
            "wgHr",
            "ilsu",
        ),
        join_keys="rcDate + rcNo + meet + chulNo",
        join_scope="self_materialized",
        output_fields=(
            "prediction_input.age",
            "prediction_input.age_prime",
            "prediction_input.allowance_flag",
            "prediction_input.class_code",
            "prediction_input.draw_no",
            "prediction_input.rating",
            "prediction_input.rest_days",
            "prediction_input.rest_risk_code",
            "prediction_input.sex_code",
            "prediction_input.wgBudam",
            "prediction_input.wgHr_value",
        ),
        availability_stage="L0",
        as_of_requirement="DIRECT_PRE_RACE",
        late_update_rule="pre-cutoff 최신 리비전만 잠그고 cutoff 이후 재발행은 잠긴 입력을 덮어쓰지 않는다",
        train_inference_flag="ALLOW",
        operational_status="허용",
        evidence_refs=(*_RULE_REFS, *_API_PIPELINE_REFS),
        notes="기본 출전표 카드의 비시장 사전 정보 블록",
    ),
    _row(
        source_block_id="entry_card_postrace_fields",
        source_system="KRA_API",
        source_object="API214_1.response.body.items.item[]",
        storage_path="races.raw_data.tagged_field_shadow.*",
        grain="race_entry",
        source_columns=(
            "ord",
            "ordBigo",
            "rankRise",
            "diffUnit",
            "buG1fOrd",
            "buG2fOrd",
            "buG3fOrd",
            "buG4fOrd",
            "buS1fOrd",
            "sjG1fOrd",
            "sjG3fOrd",
            "sjS1fOrd",
            "buG1fAccTime",
            "buG2fAccTime",
            "buG3fAccTime",
            "buG4fAccTime",
            "buS1fAccTime",
        ),
        join_keys="같은 API214_1 row 내부 혼입",
        join_scope="self_materialized",
        output_fields=("blocked_source.current_race_postrace_fields",),
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        late_update_rule="raw/shadow 보존만 허용하고 feature 생성·조인에서는 항상 차단",
        train_inference_flag="BLOCK",
        operational_status="금지",
        evidence_refs=(
            "docs/prerace-data-whitelist-blacklist-policy.md",
            "packages/scripts/evaluation/leakage_checks.py",
            "apps/api/services/prerace_storage_policy.py",
        ),
        notes="동일 원천 API 안에 섞여 들어오는 사후 결과/구간기록 블록",
    ),
    _row(
        source_block_id="entry_card_market_odds",
        source_system="KRA_API",
        source_object="API214_1.response.body.items.item[]",
        storage_path="races.basic_data.horses[]",
        grain="race_entry",
        source_columns=("winOdds", "plcOdds"),
        join_keys="rcDate + rcNo + meet + chulNo",
        join_scope="self_materialized",
        output_fields=(
            "prediction_input.odds_rank",
            "prediction_input.plcOdds",
            "prediction_input.plcOdds_rr",
            "prediction_input.winOdds",
            "prediction_input.winOdds_rr",
        ),
        availability_stage="?",
        as_of_requirement="TIMING_UNVERIFIED",
        late_update_rule="실측 로그로 pre-cutoff 공개가 확인되기 전까지 raw 저장과 연구만 허용",
        train_inference_flag="HOLD",
        operational_status="보류",
        evidence_refs=(
            "docs/prerace-data-whitelist-blacklist-policy.md",
            "docs/kra-race-lifecycle-timing-matrix.md",
            "data/contracts/prediction_input_field_registry_v1.csv",
        ),
        notes="시장 odds와 odds 의존 파생은 최종 운영 기준선에서 보류",
    ),
    _row(
        source_block_id="race_plan_feature_block",
        source_system="KRA_API",
        source_object="API72_2.response.body.items.item",
        storage_path="races.basic_data.race_plan",
        grain="race",
        source_columns=("rank", "budam", "rcDist", "ageCond", "sexCond"),
        join_keys="rcDate + rcNo + meet",
        join_scope="race_key",
        output_fields=(
            "prediction_input.budam_code",
            "prediction_input.dist",
            "prediction_input.is_handicap",
            "prediction_input.is_mile",
            "prediction_input.is_route",
            "prediction_input.is_sprint",
        ),
        availability_stage="L-1",
        as_of_requirement="DIRECT_PRE_RACE",
        late_update_rule="pre-cutoff 최신 정상 row만 채택하고 cutoff 이후 정정은 잠긴 입력에 반영하지 않는다",
        train_inference_flag="ALLOW",
        operational_status="허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="경주 조건과 거리 기반 파생의 upstream",
    ),
    _row(
        source_block_id="race_plan_cutoff_anchor",
        source_system="KRA_API",
        source_object="API72_2.response.body.items.item",
        storage_path="races.basic_data.race_plan.sch_st_time",
        grain="race",
        source_columns=("schStTime",),
        join_keys="rcDate + rcNo + meet",
        join_scope="race_key",
        output_fields=("metadata.operational_cutoff_at", "metadata.entry_finalized_at"),
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        late_update_rule="scheduled_start_at 기준 cutoff를 계산한 뒤 cutoff 이후 재발행은 감사 로그만 남긴다",
        train_inference_flag="META_ONLY",
        operational_status="메타 전용",
        evidence_refs=(
            "docs/holdout-entry-finalization-rule.md",
            "docs/holdout-snapshot-filtering-format.md",
            "docs/kra-race-lifecycle-timing-matrix.md",
        ),
        notes="피처는 아니지만 출전표 확정 시점 이후 정보 여부를 판정하는 핵심 anchor",
    ),
    _row(
        source_block_id="track_snapshot_block",
        source_system="KRA_API",
        source_object="API189_1.response.body.items.item",
        storage_path="races.basic_data.track",
        grain="race",
        source_columns=("weather", "track", "waterPercent"),
        join_keys="rcDate + rcNo + meet",
        join_scope="race_key",
        output_fields=(
            "prediction_input.track_pct",
            "prediction_input.weather_code",
            "prediction_input.wet_track",
        ),
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        late_update_rule="cutoff 이전 snapshot만 허용하고 이후 주로 변동은 잠긴 입력을 갱신하지 않는다",
        train_inference_flag="ALLOW_SNAPSHOT_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="날씨/주로 상태는 변동 가능하므로 snapshot 고정이 필수",
    ),
    _row(
        source_block_id="cancelled_horses_snapshot_block",
        source_system="KRA_API",
        source_object="API9_1.response.body.items.item[]",
        storage_path="races.basic_data.cancelled_horses[]",
        grain="race_entry",
        source_columns=("chulNo", "hrNo", "hrName", "cancelReason"),
        join_keys="rcDate + rcNo + meet (+ chulNo)",
        join_scope="race_key",
        output_fields=(
            "prediction_input.cancelled_count",
            "prediction_input.field_size_live",
        ),
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        late_update_rule="cutoff 이후 추가 취소는 운영 로그에만 남기고 잠긴 field_size_live를 덮어쓰지 않는다",
        train_inference_flag="ALLOW_SNAPSHOT_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="실출전 두수와 취소 카운트는 cutoff 이전 취소 목록만 사용",
    ),
    _row(
        source_block_id="same_race_core_aggregates",
        source_system="INTERNAL_DERIVED",
        source_object="same-race aggregate over races.basic_data.horses[]",
        storage_path="races.enriched_data.horses[].computed_features",
        grain="race_entry",
        source_columns=("rating", "wgBudam", "wgHr", "chulNo"),
        join_keys="same race_id, ordered by chul_no",
        join_scope="same_race_aggregate",
        output_fields=(
            "prediction_input.burden_ratio",
            "prediction_input.draw_rr",
            "prediction_input.field_size",
            "prediction_input.is_large",
            "prediction_input.rating_rank",
            "prediction_input.rating_rr",
            "prediction_input.wgBudam_rr",
            "prediction_input.wg_budam_rank",
        ),
        availability_stage="L0",
        as_of_requirement="DIRECT_PRE_RACE",
        late_update_rule="부모 entry_card_core snapshot이 잠긴 뒤에만 같은 경주 집계를 재계산한다",
        train_inference_flag="ALLOW",
        operational_status="허용",
        evidence_refs=(
            *_FEATURE_REFS,
            "packages/scripts/shared/prerace_field_policy.py",
        ),
        notes="현재 경주 내부 순위/상대화 파생",
    ),
    _row(
        source_block_id="horse_detail_history_block",
        source_system="KRA_API",
        source_object="API8_2.response.body.items.item",
        storage_path="races.basic_data.horses[].hrDetail",
        grain="horse",
        source_columns=(
            "hrNo",
            "rcCntT",
            "rcCntY",
            "ord1CntT",
            "ord2CntT",
            "ord3CntT",
            "ord1CntY",
            "ord2CntY",
            "ord3CntY",
            "totalPrize",
        ),
        join_keys="horses[].hr_no -> API8_2.hrNo",
        join_scope="horse_id",
        output_fields=(
            "prediction_input.horse_low_sample",
            "prediction_input.horse_place_rate",
            "prediction_input.horse_starts_y",
            "prediction_input.horse_top3_skill",
            "prediction_input.horse_win_rate",
            "prediction_input.hr_starts_t",
            "prediction_input.hr_starts_y",
            "prediction_input.total_place_rate",
            "prediction_input.year_place_rate",
        ),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="과거 재조회 최신값이 아니라 당시 저장본만 허용하고 누락 시 null 유지",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="말 누적 이력은 사전 정보지만 시점 오염을 막기 위해 stored-only",
    ),
    _row(
        source_block_id="jockey_detail_history_block",
        source_system="KRA_API",
        source_object="API12_1.response.body.items.item",
        storage_path="races.basic_data.horses[].jkDetail",
        grain="jockey",
        source_columns=(
            "jkNo",
            "rcCntT",
            "rcCntY",
            "ord1CntT",
            "ord2CntT",
            "ord3CntT",
            "ord1CntY",
            "ord2CntY",
            "ord3CntY",
            "winRateT",
            "winRateY",
        ),
        join_keys="horses[].jk_no -> API12_1.jkNo",
        join_scope="jockey_id",
        output_fields=(
            "prediction_input.jk_place_rate_y",
            "prediction_input.jockey_form",
            "prediction_input.jockey_place_rate",
            "prediction_input.jockey_recent_win_rate",
            "prediction_input.jockey_total_place_rate",
            "prediction_input.jockey_win_rate",
        ),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="당시 저장본만 허용하고 재조회 최신값으로 덮어쓰지 않는다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="기수 누적 성적 detail 블록",
    ),
    _row(
        source_block_id="trainer_detail_history_block",
        source_system="KRA_API",
        source_object="API19_1.response.body.items.item",
        storage_path="races.basic_data.horses[].trDetail",
        grain="trainer",
        source_columns=(
            "trNo",
            "rcCntT",
            "rcCntY",
            "ord1CntT",
            "ord2CntT",
            "ord3CntT",
            "ord1CntY",
            "ord2CntY",
            "ord3CntY",
            "plcRateT",
            "plcRateY",
            "winRateT",
            "winRateY",
        ),
        join_keys="horses[].tr_no -> API19_1.trNo",
        join_scope="trainer_id",
        output_fields=(
            "prediction_input.tr_place_rate_y",
            "prediction_input.tr_skill",
            "prediction_input.trainer_place_rate",
            "prediction_input.trainer_total_place_rate",
            "prediction_input.trainer_win_rate",
        ),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="당시 저장본만 허용하고 재조회 최신값으로 덮어쓰지 않는다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="조교사 누적 성적 detail 블록",
    ),
    _row(
        source_block_id="jockey_stats_history_block",
        source_system="KRA_API",
        source_object="API11_1.response.body.items.item",
        storage_path="races.basic_data.horses[].jkStats",
        grain="jockey",
        source_columns=("jkNo", "meet", "qnlRateY", "qnlRateT", "rcCntY"),
        join_keys="horses[].jk_no + meet -> API11_1.jkNo + meet",
        join_scope="jockey_id",
        output_fields=("prediction_input.jk_skill",),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="당시 저장본만 허용하고 같은 기수의 이후 누적 갱신으로 덮어쓰지 않는다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="기수 통계 전용 API11_1 블록",
    ),
    _row(
        source_block_id="owner_detail_history_block",
        source_system="KRA_API",
        source_object="API14_1.response.body.items.item",
        storage_path="races.basic_data.horses[].owDetail",
        grain="owner",
        source_columns=("owNo", "rcCntT", "rcCntY", "ord1CntT", "ord1CntY"),
        join_keys="horses[].ow_no -> API14_1.owNo (fallback: horses[].hrDetail.ow_no)",
        join_scope="owner_id",
        output_fields=(
            "prediction_input.owner_skill",
            "prediction_input.owner_win_rate",
        ),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="owner ID fallback은 허용하지만 값은 당시 저장본만 사용한다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="마주 상세/누적 정보",
    ),
    _row(
        source_block_id="training_snapshot_block",
        source_system="KRA_API",
        source_object="API329.response.body.items.item[]",
        storage_path="races.basic_data.horses[].training",
        grain="horse",
        source_columns=("hrName", "remkTxt", "trngDt"),
        join_keys="horses[].hr_name -> API329.hrName",
        join_scope="horse_name_fallback",
        output_fields=(
            "prediction_input.days_since_training",
            "prediction_input.recent_training",
            "prediction_input.training_score",
        ),
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        late_update_rule="이름 매칭 실패는 soft-fail empty block, cutoff 이후 추가 조교 정보는 잠긴 입력에 반영하지 않는다",
        train_inference_flag="ALLOW_SNAPSHOT_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_RULE_REFS,
            "docs/prerace-source-schema.md",
            *_API_PIPELINE_REFS,
        ),
        notes="숫자 key가 없는 이름 매칭 조인이라 soft-fail 규칙이 필수",
    ),
    _row(
        source_block_id="same_race_stored_feature_aggregates",
        source_system="INTERNAL_DERIVED",
        source_object="same-race aggregate over stored-only feature blocks",
        storage_path="races.enriched_data.horses[].computed_features",
        grain="race_entry",
        source_columns=(
            "horse_place_rate",
            "jockey_place_rate",
            "trainer_place_rate",
            "year_place_rate",
            "total_place_rate",
            "horse_top3_skill",
            "jk_skill",
            "tr_skill",
        ),
        join_keys="same race_id, ordered by chul_no",
        join_scope="same_race_aggregate",
        output_fields=(
            "prediction_input.gap_3rd_4th",
            "prediction_input.horse_place_rate_rr",
            "prediction_input.horse_skill_rank",
            "prediction_input.jk_skill_rank",
            "prediction_input.jockey_place_rate_rr",
            "prediction_input.total_place_rate_rr",
            "prediction_input.tr_skill_rank",
            "prediction_input.trainer_place_rate_rr",
            "prediction_input.year_place_rate_rr",
        ),
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        late_update_rule="부모 stored-only 블록이 시점 고정된 경우에만 같은 경주 상대화 파생을 계산한다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="조건부 허용",
        evidence_refs=(
            *_FEATURE_REFS,
            "packages/scripts/shared/prerace_field_policy.py",
        ),
        notes="stored-only 부모 피처의 race-relative 파생",
    ),
    _row(
        source_block_id="historical_result_lookback_block",
        source_system="POSTGRES",
        source_object="races.basic_data + races.result_data historical lookup",
        storage_path="horses[].past_stats",
        grain="horse",
        source_columns=("basic_data.horses[].hr_no", "result_data.top3", "date"),
        join_keys="current.horses[].hr_no -> historical.horses[].hr_no AND historical.date < current.race_date",
        join_scope="historical_lookup",
        output_fields=(
            "computed_feature.recent_race_count",
            "computed_feature.recent_top3_rate",
            "computed_feature.recent_win_rate",
        ),
        availability_stage="L-1",
        as_of_requirement="HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
        late_update_rule="현재 경주보다 이전 날짜의 확정 결과만 집계하고 같은 날/미래 날짜 row는 제외한다",
        train_inference_flag="ALLOW_STORED_ONLY",
        operational_status="선택",
        evidence_refs=(*_DB_REFS, "packages/scripts/tests/test_past_top3_stats.py"),
        notes="현재 SAFE_FEATURES에는 미연결이지만 feature_engineering이 이미 지원하는 과거 결과 기반 lookback",
    ),
    _row(
        source_block_id="race_odds_postrace_block",
        source_system="POSTGRES",
        source_object="race_odds",
        storage_path="race_odds.*",
        grain="race_odds_row",
        source_columns=(
            "pool",
            "odds",
            "chul_no",
            "chul_no2",
            "chul_no3",
            "collected_at",
        ),
        join_keys="race_id + pool + chul_no + chul_no2 + chul_no3 + source",
        join_scope="postrace_feedback",
        output_fields=("blocked_source.race_odds",),
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        late_update_rule="분석/감사에는 남기되 학습/추론 feature 조인에서는 항상 차단",
        train_inference_flag="BLOCK",
        operational_status="금지",
        evidence_refs=(
            "docs/table-column-availability-map.md",
            "apps/api/services/result_collection_service.py",
            "apps/api/migrations/003_add_race_odds.sql",
        ),
        notes="결과 직후 수집되는 확정 배당 테이블",
    ),
    _row(
        source_block_id="prediction_feedback_block",
        source_system="POSTGRES",
        source_object="predictions",
        storage_path="predictions.*",
        grain="prediction_row",
        source_columns=(
            "actual_result",
            "accuracy_score",
            "correct_count",
            "created_at",
        ),
        join_keys="predictions.race_id",
        join_scope="postrace_feedback",
        output_fields=("blocked_source.prediction_feedback",),
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        late_update_rule="평가/모니터링 용도로만 사용하고 feature 조인에서는 항상 차단",
        train_inference_flag="BLOCK",
        operational_status="금지",
        evidence_refs=(
            "docs/table-column-availability-map.md",
            "apps/api/migrations/001_unified_schema.sql",
        ),
        notes="예측 성능 피드백 테이블은 현재 경주 입력으로 사용할 수 없다",
    ),
)


def canonical_feature_source_timing_rows() -> tuple[dict[str, str], ...]:
    return tuple(row.to_csv_row() for row in FEATURE_SOURCE_TIMING_ROWS)


def contract_row_by_id(source_block_id: str) -> FeatureSourceTimingRow | None:
    for row in FEATURE_SOURCE_TIMING_ROWS:
        if row.source_block_id == source_block_id:
            return row
    return None


def rows_for_output_field(output_field: str) -> tuple[FeatureSourceTimingRow, ...]:
    return tuple(
        row for row in FEATURE_SOURCE_TIMING_ROWS if row.covers_output(output_field)
    )


def covered_prediction_inputs() -> tuple[str, ...]:
    names: list[str] = []
    for row in FEATURE_SOURCE_TIMING_ROWS:
        for output_field in row.output_fields:
            if output_field.startswith("prediction_input."):
                names.append(output_field.removeprefix("prediction_input."))
    return tuple(sorted(set(names)))
