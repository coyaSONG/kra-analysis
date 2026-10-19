"""Exact repository admission for the PR110 development-only experiment."""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path

import numpy as np
import scipy
from threadpoolctl import threadpool_info

from autoresearch.condition_training_data import prepare
from autoresearch.condition_training_model import RECIPE
from autoresearch.restricted_cohort import ROOT, encoded, parse_json, sha256

REGISTRY = "data/contracts/condition_training_reviews_v1.json"
COHORT_SHA = "c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03"
PINS = {
    "cohort": (
        ".cache/autoresearch/development-source-audit-20261018/run-1/development-cohort.json",
        COHORT_SHA,
    ),
    "matrix": (
        ".cache/autoresearch/condition-candidate-inputs-20261015/run-1/matrix.json",
        "7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1",
    ),
    "outcomes": (
        ".cache/autoresearch/forward-outcomes/20261018T094903.670114Z/outcomes.json",
        "0cf7be483e1089ba55db78f70c51c9a6dbcaf8738847460f469ee11901ac0cbb",
    ),
    "source_audit": (
        ".cache/autoresearch/development-source-audit-20261018/run-1/audit.json",
        "56255f1cca70ba40aabad36f852da5bb831d3e4aeb9a28fc2671c100cd844d37",
    ),
    "baseline_audit": (
        ".cache/autoresearch/baseline-lineage-audit-20261018/run-1/audit.json",
        "8dfaf0063472a8f811e25cdaad14c43be97d269abef59921a502fced3d5fba4f",
    ),
    "m0": (
        "docs/research/commitments/2026-10-16-18/m0.json",
        "de82b4d1dc1d69b7982af04b7d83557d008381ea23202f0dff661721388f7a2c",
    ),
    "api27": (
        "docs/research/commitments/2026-10-16-18/api27.json",
        "a51f7b8ca425251fa6bc7602788031a6675b3b9de195c55db76789d5847f6646",
    ),
    "training_inputs": (
        "docs/research/commitments/2026-10-16-18/training-inputs.json",
        "b4ab302c93bb01a947bd149622770d3413690f5fa95bbec8c13a00ed2808fa32",
    ),
}
EXCEPTION_RACES = ["20261016_3_8", "20261017_1_3", "20261017_1_4", "20261018_1_6"]
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
)


def git(*args):
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE
    )


def read(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("missing_or_oversized_evidence")
    return path.read_bytes()


def pinned(path, expected):
    raw = read(path)
    if sha256(raw) != expected:
        raise ValueError(f"input_hash_mismatch:{Path(path).name}")
    return parse_json(raw)


def implementation():
    files = sorted(
        p
        for p in (ROOT / "packages/scripts").rglob("*.py")
        if "tests" not in p.parts and ".venv" not in p.parts
    )
    files += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    return {str(p.relative_to(ROOT)): sha256(read(p)) for p in files}


def environment():
    libraries = []
    for library in threadpool_info():
        record = dict(library)
        path = Path(record.pop("filepath"))
        record.update(filename=path.name, sha256=sha256(path.read_bytes()))
        libraries.append(record)
    cpu = platform.processor()
    if platform.system() == "Darwin":
        cpu = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
        "numpy_build": np.show_config(mode="dicts"),
        "scipy_build": scipy.show_config(mode="dicts"),
        "libraries": sorted(libraries, key=lambda r: r["filename"]),
        "packages": sorted((d.metadata["Name"], d.version) for d in distributions()),
        "thread_settings": {k: os.environ.get(k) for k in THREAD_VARIABLES},
    }


def load():
    inputs = {
        name: pinned(ROOT / path, digest) for name, (path, digest) in PINS.items()
    }
    cohort, matrix = inputs["cohort"], inputs["matrix"]
    if (
        cohort["feature_matrix_sha256"] != PINS["matrix"][1]
        or cohort["outcomes_sha256"] != PINS["outcomes"][1]
        or encoded(cohort["source_pins"]) != encoded(matrix["source_pins"])
    ):
        raise ValueError("input_link_mismatch")
    packets, pins = [], {str(ROOT / p): h for p, h in PINS.values()}
    for pin in cohort["source_pins"]["packets"]:
        packet = pinned(pin["path"], pin["sha256"])
        if packet["race_id"] != pin["race_id"]:
            raise ValueError("packet_identity_mismatch")
        packets.append(packet)
        pins[pin["path"]] = pin["sha256"]
    public_ids = [r["race_id"] for d in inputs["m0"]["days"] for r in d["races"]]
    x, y, weights, identities, summary = prepare(
        cohort, matrix, inputs["outcomes"], packets, public_ids
    )
    if (
        summary["race_count"],
        summary["row_count"],
        summary["positive"],
        summary["negative"],
    ) != (50, 534, 150, 384):
        raise ValueError("fixed_population_mismatch")
    if sorted(r["race_id"] for r in summary["exceptions"]) != EXCEPTION_RACES:
        raise ValueError("fixed_exceptions_mismatch")
    requirement = {
        "format_version": "condition-training-admission-v1",
        "purpose": "research_fit_only",
        "inputs": pins,
        "implementation": implementation(),
        "environment": environment(),
        "recipe": RECIPE,
        "summary": summary,
        "selected_race_ids": sorted(public_ids),
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
        "independent_validation_eligible": False,
    }
    # Canonical round-trip removes tuple/list representation differences.
    return (x, y, weights, identities), parse_json(encoded(requirement))


def approval(requirement):
    raw = read(ROOT / REGISTRY)
    registry = parse_json(raw)
    if registry.get("format_version") != "condition-training-reviews-v1":
        raise ValueError("invalid_approval_registry")
    digest = sha256(encoded(requirement))
    matches = [
        r for r in registry["approved_recipes"] if r.get("requirement_sha256") == digest
    ]
    if len(matches) != 1:
        raise ValueError("exact_repository_approval_required")
    review = matches[0]
    for flag in (
        "source_review_complete",
        "label_version_review_complete",
        "implementation_review_complete",
    ):
        if review.get(flag) is not True:
            raise ValueError("incomplete_review")
    if (
        review.get("purpose") != "research_fit_only"
        or review.get("fit_budget") != {"A24": 1, "B34": 1}
        or not isinstance(review.get("review_id"), str)
        or not review["review_id"].strip()
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
    ):
        raise ValueError("invalid_review")
    reviewed = datetime.fromisoformat(review["reviewed_at"])
    if reviewed.utcoffset() is None or reviewed > datetime.now(UTC):
        raise ValueError("invalid_review_clock")
    # A locally invented/uncommitted registry is not repository approval.
    if git("show", f"HEAD:{REGISTRY}") != raw:
        raise ValueError("uncommitted_approval")
    if git("show", f"origin/main:{REGISTRY}") != raw:
        raise ValueError("approval_not_on_main")
    for path, digest in requirement["implementation"].items():
        if sha256(git("show", f"HEAD:{path}")) != digest:
            raise ValueError("uncommitted_implementation")
    return raw, review


def unchanged(requirement, registry):
    if read(ROOT / REGISTRY) != registry:
        raise ValueError("approval_changed_during_run")
    for path, digest in requirement["inputs"].items():
        if sha256(read(path)) != digest:
            raise ValueError("original_input_changed_during_run")
    if implementation() != requirement["implementation"] or encoded(
        environment()
    ) != encoded(requirement["environment"]):
        raise ValueError("implementation_or_environment_changed_during_run")
