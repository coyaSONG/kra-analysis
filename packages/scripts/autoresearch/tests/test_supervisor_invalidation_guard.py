from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from run_autoresearch_supervisor import (  # noqa: E402
    INVALIDATION_NOTICE,
    assert_research_not_invalidated,
)


def test_supervisor_refuses_to_start_when_results_are_invalidated(
    tmp_path: Path,
) -> None:
    (tmp_path / INVALIDATION_NOTICE).write_text(
        "Status: `INVALID_LEAKAGE`\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="INVALID_LEAKAGE"):
        assert_research_not_invalidated(
            tmp_path,
            results_path=tmp_path / "autoresearch-results.tsv",
            allow_invalidated_results=False,
        )


def test_supervisor_allows_explicit_manual_recovery_override(tmp_path: Path) -> None:
    (tmp_path / INVALIDATION_NOTICE).write_text(
        "Status: `INVALID_LEAKAGE`\n",
        encoding="utf-8",
    )

    assert_research_not_invalidated(
        tmp_path,
        results_path=tmp_path / "autoresearch-results.tsv",
        allow_invalidated_results=True,
    )


def test_supervisor_allows_clean_restarted_results_file(tmp_path: Path) -> None:
    (tmp_path / INVALIDATION_NOTICE).write_text(
        "Status: `INVALID_LEAKAGE`\n",
        encoding="utf-8",
    )

    assert_research_not_invalidated(
        tmp_path,
        results_path=tmp_path / "autoresearch-results-clean-v2.tsv",
        allow_invalidated_results=False,
    )
