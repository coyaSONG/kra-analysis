"""T-30 operational release feature overlay contract."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

T30_RELEASE_CONTRACT_VERSION = "t30-operational-release-features-v1"
T30_RELEASE_CONTRACT_RELATIVE_PATH = Path(
    "data/contracts/t30_operational_release_features_v1.csv"
)
ROOT_DIR = Path(__file__).resolve().parents[3]
T30_RELEASE_CONTRACT_PATH = ROOT_DIR / T30_RELEASE_CONTRACT_RELATIVE_PATH
T30_RELEASE_BUCKETS = frozenset({"RELEASE", "BACKFILL_ONLY", "AUDIT_ONLY", "EXCLUDE"})
T30_MODEL_FEATURE_STATUSES = frozenset(
    {
        "current_model_input",
        "planned_model_input",
        "planned_nullable",
        "backfill_only",
        "audit_only",
        "excluded",
    }
)


@dataclass(frozen=True, slots=True)
class T30ReleaseFeatureSpec:
    feature_name: str
    feature_group: str
    release_bucket: str
    cutoff_rule: str
    model_feature_status: str
    notes: str

    def __post_init__(self) -> None:
        if self.release_bucket not in T30_RELEASE_BUCKETS:
            raise ValueError(
                f"unsupported T-30 release bucket for {self.feature_name}: "
                f"{self.release_bucket}"
            )
        if self.model_feature_status not in T30_MODEL_FEATURE_STATUSES:
            raise ValueError(
                f"unsupported T-30 model feature status for {self.feature_name}: "
                f"{self.model_feature_status}"
            )
        if not self.feature_name:
            raise ValueError("T-30 feature_name must be non-empty")
        if not self.cutoff_rule:
            raise ValueError(f"T-30 cutoff_rule must be non-empty: {self.feature_name}")

    @property
    def is_release_feature(self) -> bool:
        return self.release_bucket == "RELEASE"

    @property
    def is_current_model_input(self) -> bool:
        return self.model_feature_status == "current_model_input"


def load_t30_release_feature_specs(
    path: Path = T30_RELEASE_CONTRACT_PATH,
) -> tuple[T30ReleaseFeatureSpec, ...]:
    """Load and validate the T-30 operational release feature overlay."""

    with path.open(encoding="utf-8", newline="") as handle:
        rows = [T30ReleaseFeatureSpec(**row) for row in csv.DictReader(handle)]

    names = [row.feature_name for row in rows]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate T-30 release feature names: {duplicates}")
    return tuple(rows)


T30_RELEASE_FEATURE_SPECS: tuple[T30ReleaseFeatureSpec, ...] = (
    load_t30_release_feature_specs()
)
T30_RELEASE_FEATURE_BY_NAME: dict[str, T30ReleaseFeatureSpec] = {
    spec.feature_name: spec for spec in T30_RELEASE_FEATURE_SPECS
}


def t30_feature_names_by_bucket(bucket: str) -> tuple[str, ...]:
    """Return feature names for one T-30 release bucket."""

    if bucket not in T30_RELEASE_BUCKETS:
        raise ValueError(f"unsupported T-30 release bucket: {bucket}")
    return tuple(
        spec.feature_name
        for spec in T30_RELEASE_FEATURE_SPECS
        if spec.release_bucket == bucket
    )


def t30_release_feature_names(*, current_model_only: bool = False) -> tuple[str, ...]:
    """Return T-30 release overlay feature names.

    By default this includes planned release fields such as `weight_delta` and
    `changed_jockey_flag`. Pass `current_model_only=True` when validating the
    current row schema without requiring planned fields to exist yet.
    """

    return tuple(
        spec.feature_name
        for spec in T30_RELEASE_FEATURE_SPECS
        if spec.is_release_feature
        and (not current_model_only or spec.is_current_model_input)
    )


def t30_disallowed_overlay_feature_names() -> tuple[str, ...]:
    """Return contracted overlay fields that cannot appear in release rows."""

    return tuple(
        spec.feature_name
        for spec in T30_RELEASE_FEATURE_SPECS
        if not spec.is_release_feature
    )


def validate_t30_release_overlay_features(
    feature_names: list[str] | tuple[str, ...],
) -> None:
    """Fail if a selected feature contains audit-only or backfill-only overlays.

    The overlay contract intentionally does not list every core-card model
    feature. Unlisted core features are ignored here and remain governed by the
    main prediction input registry.
    """

    selected = set(feature_names)
    disallowed = sorted(selected & set(t30_disallowed_overlay_feature_names()))
    if disallowed:
        detail = {
            name: T30_RELEASE_FEATURE_BY_NAME[name].release_bucket
            for name in disallowed
        }
        raise ValueError(
            f"T-30 release feature set contains non-release overlays: {detail}"
        )
