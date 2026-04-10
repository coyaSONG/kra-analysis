"""Autoresearch 재현성 매니페스트 저장 계약."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from shared.execution_matrix import validate_evaluation_seeds

REPRODUCIBILITY_MANIFEST_VERSION = "autoresearch-reproducibility-manifest-v1"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _normalize_sha256(value: str, *, field_name: str) -> str:
    lowered = value.lower()
    if len(lowered) != 64 or any(ch not in "0123456789abcdef" for ch in lowered):
        raise ValueError(f"{field_name} 는 64자리 hexadecimal 이어야 한다.")
    return lowered


class ArtifactHashRecord(_FrozenModel):
    """입출력 아티팩트 해시 레코드."""

    artifact_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    byte_size: int = Field(ge=0)
    generated_at: datetime | None = None

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return _normalize_sha256(value, field_name="sha256")


class SourceDataVersion(_FrozenModel):
    """원천 데이터 버전과 그 계산 근거."""

    dataset: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    artifact_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("artifact_ids")
    @classmethod
    def _validate_artifact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source_data.artifact_ids 에 중복 값을 넣을 수 없다.")
        return value


class RunConfiguration(_FrozenModel):
    """실험 설정값 스냅샷."""

    config_path: str = Field(min_length=1)
    config_sha256: str = Field(min_length=64, max_length=64)
    settings: dict[str, Any]

    @field_validator("config_sha256")
    @classmethod
    def _validate_config_sha256(cls, value: str) -> str:
        return _normalize_sha256(value, field_name="configuration.config_sha256")


class SeedEnvelope(_FrozenModel):
    """재현성에 필요한 시드 묶음."""

    model_random_state: int | None = None
    selection_seed: int | None = None
    selection_seed_invariant: bool | None = None
    evaluation_seeds: tuple[int, ...] = ()

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value, allow_empty=True)


class SplitManifestReference(_FrozenModel):
    """평가에 사용한 분할 결과 manifest 참조."""

    artifact_id: str | None = None
    manifest_path: str | None = None
    manifest_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    included_race_count: int | None = Field(default=None, ge=1)
    included_race_ids_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    selection_seed: int | None = None
    selection_seed_invariant: bool | None = None
    evaluation_seeds: tuple[int, ...] = ()

    @field_validator("manifest_sha256", "included_race_ids_sha256")
    @classmethod
    def _validate_optional_sha256(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return _normalize_sha256(value, field_name=str(info.field_name))

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value, allow_empty=True)

    @model_validator(mode="after")
    def _validate_reference_shape(self) -> SplitManifestReference:
        has_reference_value = any(
            value is not None
            for value in (self.artifact_id, self.manifest_path, self.manifest_sha256)
        )
        if not has_reference_value:
            if (
                self.included_race_count is not None
                or self.included_race_ids_sha256 is not None
            ):
                raise ValueError(
                    "split reference 없이 included_race_count 또는 included_race_ids_sha256 를 기록할 수 없다."
                )
            if (
                self.selection_seed is not None
                or self.selection_seed_invariant is not None
            ):
                raise ValueError(
                    "split reference 없이 selection seed 정보를 기록할 수 없다."
                )
            if self.evaluation_seeds:
                raise ValueError(
                    "split reference 없이 evaluation_seeds 를 기록할 수 없다."
                )
            return self

        missing = [
            name
            for name, value in (
                ("artifact_id", self.artifact_id),
                ("manifest_path", self.manifest_path),
                ("manifest_sha256", self.manifest_sha256),
            )
            if value is None
        ]
        if missing:
            raise ValueError(
                "split reference 는 artifact_id, manifest_path, manifest_sha256 를 함께 가져야 한다: "
                f"missing={missing}"
            )
        if (
            self.included_race_count is not None
            and self.included_race_ids_sha256 is None
        ):
            raise ValueError(
                "included_race_count 를 기록할 때는 included_race_ids_sha256 도 함께 기록해야 한다."
            )
        return self


class ReproducibilityManifest(_FrozenModel):
    """Autoresearch 평가 결과의 재현성 매니페스트."""

    format_version: Literal["autoresearch-reproducibility-manifest-v1"] = (
        REPRODUCIBILITY_MANIFEST_VERSION
    )
    run_type: Literal["research_evaluation"]
    run_created_at: datetime
    source_data: SourceDataVersion
    configuration: RunConfiguration
    seeds: SeedEnvelope
    split: SplitManifestReference | None = None
    artifacts: tuple[ArtifactHashRecord, ...] = Field(min_length=1)
    manifest_sha256: str | None = None

    @field_validator("artifacts")
    @classmethod
    def _validate_artifacts(
        cls, value: tuple[ArtifactHashRecord, ...]
    ) -> tuple[ArtifactHashRecord, ...]:
        artifact_ids = [item.artifact_id for item in value]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("artifacts.artifact_id 는 중복될 수 없다.")
        return value


def reproducibility_manifest_json_schema() -> dict[str, Any]:
    """외부 저장/검증에 사용할 JSON schema dict를 반환한다."""

    return ReproducibilityManifest.model_json_schema()


def validate_reproducibility_manifest(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    """재현성 매니페스트 payload를 검증하고 오류 메시지를 정규화해서 반환한다."""

    try:
        ReproducibilityManifest.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []
