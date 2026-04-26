#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

INVALIDATION_NOTICE = "AUTORESEARCH_INVALIDATION.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_iteration_count(results_path: Path) -> int:
    if not results_path.exists():
        return 0
    count = 0
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("iteration\t"):
            continue
        count += 1
    return count


def read_max_display_iteration(results_path: Path) -> int | None:
    if not results_path.exists():
        return None
    max_iteration: int | None = None
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("iteration\t"):
            continue
        first_column = line.split("\t", 1)[0]
        try:
            iteration = int(first_column)
        except ValueError:
            continue
        if max_iteration is None or iteration > max_iteration:
            max_iteration = iteration
    return max_iteration


def git_status_clean(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip() == ""


def update_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def assert_research_not_invalidated(
    repo: Path,
    *,
    results_path: Path,
    allow_invalidated_results: bool,
) -> None:
    invalidation_path = repo / INVALIDATION_NOTICE
    if allow_invalidated_results or not invalidation_path.exists():
        return
    if results_path.name != "autoresearch-results.tsv":
        return
    raise SystemExit(
        "autoresearch results are marked INVALID_LEAKAGE; refusing to start. "
        f"See {invalidation_path}. Remove the invalidation notice after a clean "
        "dataset/config reset, use a new clean results file, or pass "
        "--allow-invalidated-results for a manual recovery-only run."
    )


def run_codex_iteration(
    repo: Path, prompt_path: Path, log_path: Path, last_msg_path: Path
) -> int:
    with (
        prompt_path.open("r", encoding="utf-8") as prompt_file,
        log_path.open("w", encoding="utf-8") as log_file,
    ):
        proc = subprocess.run(
            [
                "codex",
                "exec",
                "-C",
                str(repo),
                "--dangerously-bypass-approvals-and-sandbox",
                "--color",
                "never",
                "--output-last-message",
                str(last_msg_path),
                "-",
            ],
            stdin=prompt_file,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument(
        "--prompt-file",
        default="AUTORESEARCH_PROMPT_ONE_ITERATION.txt",
    )
    parser.add_argument(
        "--status-file",
        default=".autoresearch/runtime/supervisor_status.json",
    )
    parser.add_argument(
        "--results-file",
        default="autoresearch-results.tsv",
    )
    parser.add_argument(
        "--allow-invalidated-results",
        action="store_true",
        help="Allow manual recovery runs even when AUTORESEARCH_INVALIDATION.md exists.",
    )
    args = parser.parse_args()

    repo = Path.cwd()
    prompt_path = repo / args.prompt_file
    status_path = repo / args.status_file
    results_path = repo / args.results_file
    runtime_dir = status_path.parent
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if not prompt_path.exists():
        raise SystemExit(f"missing prompt file: {prompt_path}")
    assert_research_not_invalidated(
        repo,
        results_path=results_path,
        allow_invalidated_results=args.allow_invalidated_results,
    )
    if not git_status_clean(repo):
        raise SystemExit("working tree must be clean before supervisor start")

    starting_rows = read_iteration_count(results_path)
    starting_display_iteration = read_max_display_iteration(results_path)
    target_rows = starting_rows + args.iterations

    status_payload = {
        "state": "running",
        "started_at": utc_now(),
        "repo": str(repo),
        "starting_rows": starting_rows,
        "target_additional_iterations": args.iterations,
        "target_rows": target_rows,
        "completed_rows": starting_rows,
        "max_display_iteration": starting_display_iteration,
        "last_exit_code": None,
        "last_iteration_log": None,
        "last_message_file": None,
        "failure": None,
    }
    update_status(status_path, status_payload)

    for target_row in range(starting_rows + 1, target_rows + 1):
        log_path = runtime_dir / f"iteration-{target_row:04d}.log"
        last_msg_path = runtime_dir / f"iteration-{target_row:04d}.last.txt"
        status_payload.update(
            {
                "current_target_row": target_row,
                "current_iteration_started_at": utc_now(),
                "last_iteration_log": str(log_path),
                "last_message_file": str(last_msg_path),
            }
        )
        update_status(status_path, status_payload)

        exit_code = run_codex_iteration(repo, prompt_path, log_path, last_msg_path)
        status_payload["last_exit_code"] = exit_code

        new_rows = read_iteration_count(results_path)
        max_display_iteration = read_max_display_iteration(results_path)
        clean = git_status_clean(repo)
        status_payload["completed_rows"] = new_rows
        status_payload["max_display_iteration"] = max_display_iteration

        if exit_code != 0:
            status_payload.update(
                {
                    "state": "failed",
                    "failed_at": utc_now(),
                    "failure": {
                        "reason": "codex_exec_nonzero",
                        "exit_code": exit_code,
                        "expected_rows": target_row,
                        "actual_rows": new_rows,
                    },
                }
            )
            update_status(status_path, status_payload)
            raise SystemExit(exit_code)

        if new_rows < target_row:
            status_payload.update(
                {
                    "state": "failed",
                    "failed_at": utc_now(),
                    "failure": {
                        "reason": "iteration_row_not_appended",
                        "expected_rows": target_row,
                        "actual_rows": new_rows,
                    },
                }
            )
            update_status(status_path, status_payload)
            raise SystemExit(2)

        if not clean:
            status_payload.update(
                {
                    "state": "failed",
                    "failed_at": utc_now(),
                    "failure": {
                        "reason": "dirty_worktree_after_iteration",
                        "expected_rows": target_row,
                        "actual_rows": new_rows,
                    },
                }
            )
            update_status(status_path, status_payload)
            raise SystemExit(3)

        status_payload["completed_rows"] = new_rows
        status_payload["max_display_iteration"] = max_display_iteration
        update_status(status_path, status_payload)
        time.sleep(1)

    status_payload.update(
        {
            "state": "completed",
            "completed_at": utc_now(),
            "completed_rows": read_iteration_count(results_path),
            "max_display_iteration": read_max_display_iteration(results_path),
        }
    )
    update_status(status_path, status_payload)


if __name__ == "__main__":
    main()
