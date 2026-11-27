"""Keep audited development dependencies safe without adding API dependencies."""

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("name", "vulnerable", "minimum"),
    [
        ("aiohttp", "3.14.3", "3.14.4"),
        ("gitpython", "3.1.60", "3.2.1"),
        ("jupyter-server", "2.20.0", "2.21.1"),
        ("jupyterlab", "4.6.1", "4.6.4"),
        ("notebook", "7.6.0", "7.6.3"),
        ("soupsieve", "2.8.4", "2.9"),
        ("sqlparse", "0.5.5", "0.6.0"),
        ("tornado", "6.5.7", "6.5.9"),
        ("virtualenv", "21.14.9", "21.14.10"),
        ("werkzeug", "3.1.8", "3.1.9"),
        ("certifi", "2026.6.17", "2026.10.19"),
        ("filelock", "3.29.7", "4.2.1"),
        ("graphql-core", "3.2.11", "3.2.12"),
        ("mlflow", "3.17.0", "3.17.2"),
        ("opentelemetry-api", "1.43.0", "1.45.1"),
        ("pillow", "12.3.0", "13.0.0"),
    ],
)
def test_security_floors_match_the_shared_lock(name, vulnerable, minimum):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    constraints = {}
    for value in project["tool"]["uv"]["constraint-dependencies"]:
        requirement = Requirement(value)
        constraints[requirement.name] = requirement
    locked_constraints = {
        item["name"]: item["specifier"] for item in lock["manifest"]["constraints"]
    }
    locked = next(item["version"] for item in lock["package"] if item["name"] == name)

    assert Version(locked) >= Version(minimum)
    assert Version(locked) in constraints[name].specifier
    assert Version(vulnerable) not in constraints[name].specifier
    assert str(constraints[name].specifier) == locked_constraints[name]
