"""Internal stdlib-only entry point; execute trusted, pinned original code."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath

LIMIT = 32 * 1024 * 1024
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(value):
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or PurePosixPath(value).is_absolute()
        or any(p in ("", ".", "..") for p in value.split("/"))
    ):
        raise ValueError("snapshot_invalid_path")
    return value


def read(path):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("snapshot_symlink")
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("snapshot_oversized_file")
    return raw


def inventory(root, files):
    if type(files) is not dict or not files:
        raise ValueError("snapshot_empty_inventory")
    for name, expected in files.items():
        relative(name)
        if (
            type(expected) is not str
            or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
        ):
            raise ValueError("snapshot_invalid_digest")
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError("snapshot_symlink")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("snapshot_symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("snapshot_special_file")
        name = path.relative_to(root).as_posix()
        if name not in files:
            raise ValueError("snapshot_unlisted_file")
        actual.add(name)
        if digest(read(path)) != files[name]:
            raise ValueError("snapshot_file_hash_mismatch")
    if set(files) != actual:
        raise FileNotFoundError("snapshot_missing_files")


def source_inventory(files, implementation):
    if type(implementation) is not dict or not implementation:
        raise ValueError("snapshot_missing_implementation")
    source = {
        name: value
        for name, value in files.items()
        if name.endswith(".py") or name in ("uv.lock", "pyproject.toml")
    }
    if source != implementation or not {"uv.lock", "pyproject.toml"} <= source.keys():
        raise ValueError("snapshot_implementation_inventory_mismatch")
    for name in files:
        if name.endswith(".py") and not name.startswith("packages/scripts/"):
            raise ValueError("snapshot_source_outside_scripts")
        if Path(name).suffix in (".pyc", ".pyo", ".so", ".dylib", ".pth", ".zip"):
            raise ValueError("snapshot_unexpected_executable")


def forbidden(*args, **kwargs):
    raise ValueError("snapshot_forbidden_side_effect")


def guard_io(root):
    # Cooperative guard, not a hostile-code sandbox. Dependencies may read their
    # own installed files; original research inputs must stay within the snapshot.
    allowed = (
        root.resolve(),
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
    )

    def hook(event, args):
        if event == "open":
            path, mode, flags = args
            if (mode and any(c in mode for c in "wax+")) or flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ):
                forbidden()
            if isinstance(path, (str, bytes)):
                resolved = Path(os.fsdecode(path)).resolve()
                if not any(resolved.is_relative_to(p) for p in allowed):
                    raise ValueError("snapshot_read_outside_evidence")
        if event.startswith(("socket.", "subprocess.")) or event in (
            "os.system",
            "os.mkdir",
            "os.remove",
            "os.rmdir",
            "os.rename",
            "os.link",
            "os.symlink",
            "os.truncate",
            "os.chmod",
            "os.chown",
        ):
            forbidden()

    sys.addaudithook(hook)


def guard_execution(forward, contract, fitting, model):
    # Guard every fitting reference, including aliases already bound on import.
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    for estimator in (SimpleImputer, StandardScaler, LogisticRegression):
        for name in ("fit", "fit_transform", "partial_fit"):
            if hasattr(estimator, name):
                setattr(estimator, name, forbidden)
    fitting.fit_once = model.fit_once = fitting.run = forbidden
    fitting.save = fitting.locations = forbidden
    contract.admit = contract.training.git = forbidden
    forward.run = forward.stage = forward.witness = forward.verify_local = forbidden
    forward.locations = forbidden


def replay(request):
    root = Path(request["root"])
    files = request["files"]
    inventory(root, files)
    protocol = json.loads(read(root / relative(request["protocol"])))
    source_inventory(files, protocol["runtime"]["implementation"])
    # No autoresearch import may precede selecting the preserved source tree.
    sys.path.insert(0, str(root / "packages/scripts"))
    from autoresearch import condition_forward as forward
    from autoresearch import condition_forward_contract as contract
    from autoresearch import condition_forward_inputs as inputs
    from autoresearch import condition_training as fitting
    from autoresearch import condition_training_model as model
    from autoresearch.prerace_hash_witness import timestamp
    from autoresearch.restricted_cohort import encoded, parse_json

    protocol = parse_json(read(root / request["protocol"]))
    packet_raw = read(root / request["prediction"])
    matrix_raw = read(root / request["matrix"])
    matrix = parse_json(matrix_raw)
    packet = parse_json(packet_raw)
    if contract.ROOT.resolve() != root.resolve():
        raise ValueError("snapshot_import_root_mismatch")
    if not timestamp(matrix["created_at"]) <= timestamp(packet["computed_at"]):
        raise ValueError("snapshot_matrix_after_computation")
    observed = encoded(contract.training.environment())
    if observed != encoded(protocol["runtime"]["environment"]):
        return {
            "status": "pending_environment",
            "observed_environment_sha256": digest(observed),
        }
    guard_execution(forward, contract, fitting, model)
    guard_io(root)
    models, _ = contract.load_models()
    rebuilt, x, identities = inputs.matrix_for(
        protocol, timestamp(matrix["created_at"])
    )
    recomputed = forward.paired(
        protocol, rebuilt, x, identities, models, timestamp(packet["computed_at"])
    )
    inventory(root, files)
    matrix_matches = encoded(rebuilt) == matrix_raw
    packet_matches = encoded(recomputed) == packet_raw
    return {
        "status": "numerically_replayed"
        if matrix_matches and packet_matches
        else "replay_conflict",
        "matrix_bytes_match": matrix_matches,
        "prediction_bytes_match": packet_matches,
        "observed_environment_sha256": digest(observed),
    }


def main():
    try:
        request = json.loads(sys.stdin.buffer.read(LIMIT + 1))
        result = replay(request)
    except (ImportError, FileNotFoundError) as exc:
        result = {"status": "pending_evidence", "reason": type(exc).__name__}
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result = {"status": "replay_unverified", "reason": str(exc)}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
