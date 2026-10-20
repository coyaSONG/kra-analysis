# Original A24 B34 snapshot replay

The read-only `autoresearch.condition_snapshot_replay` command compares an
archived matrix and public paired prediction with the output of their **original
pinned implementation**. It does not use today's live admission gate, recreate
an approval, fit either model, stage new predictions, load outcomes, or register
a future interval. Dates, race IDs and N remain unset in the preregistration draft.

## Evidence required

The input is a SHA256-pinned JSON manifest with exactly these fields:

```json
{
  "format_version": "condition-snapshot-replay-v1",
  "publication": {"path": "publication.json", "sha256": "<64 hex characters>"},
  "snapshot": {
    "path": "original-snapshot",
    "files": {"<repository-relative file>": "<64 hex characters>"}
  },
  "matrix": "<repository-relative original matrix path>"
}
```

Paths are relative to the replay manifest, except snapshot `files` keys and
`matrix`, which are relative to the snapshot root. Preserve the original
repository layout. The `publication` manifest follows
[the historical publication schema](2026-10-20-condition-historical-publication.md):
original protocol, separate approval registry and prediction archives, including
GitHub response bytes and retrieval witnesses. All three chains must replay
before any original code executes.

The snapshot must contain every original `runtime.implementation` Python file,
`uv.lock`, `pyproject.toml`, original protocol/approval/prediction documents,
the two stored models and training receipt, original matrix, and all packets,
memory, schedule captures/raw pages and source receipts read by the original
matrix builder. Every file is pinned; missing files are pending. Extra unlisted
files, symlinks, mismatched hashes and added executable sources are rejected.
The implementation inventory must exactly equal the published protocol map.
An inventory hash is a replay boundary, not proof of original public availability.

## Execution and interpretation

From the research checkout, invoke the auditor using an environment matching
the original recorded environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts \
  .venv/bin/python -B -m autoresearch.condition_snapshot_replay \
  --manifest /absolute/path/to/replay.json --sha256 <manifest-sha256>
```

There is no auto-install, environment repair, network fetch, or retry. One
isolated `sys.executable -I -B` subprocess imports the snapshot's
`packages/scripts` tree. Only the six original thread variables are restored.
Original package versions, numerical library hashes/configuration, CPU,
platform, Python and thread settings must match the full recorded environment.
The import-root check prevents a fallback to the current checkout.

The original `load_models`, `matrix_for`, and `paired` functions operate at the
original matrix creation and computation timestamps. Matrix creation cannot
follow computation. Exact canonical matrix and prediction bytes must match;
there is no tolerance or favorable-triple replacement. Snapshot/public evidence
is checked again after execution. Runtime guards forbid fit/preprocessing-fit
calls, live run/admit/stage/witness paths, writes, network and subprocess work
during numerical replay. Dependency reads may use the interpreter installation;
research input reads must remain inside the snapshot.

These guards protect cooperative, reviewed repository code. They are **not an
OS security sandbox for hostile code**. Importing original pinned code and
capturing its environment precedes the execution guards; only trusted original
code whose publication chain has been verified may be supplied. Missing
dependencies or an unavailable matching environment remain unverified.

`numerically_replayed` (exit 0) means only that both archived artifacts were
reproduced. `pending_environment`, `pending_evidence` and `pending_worker`
withhold comparison. `replay_conflict` identifies byte disagreement;
`replay_unverified` identifies a replay error. Neither assigns a race-level miss.
Malformed or corrupt evidence is blocked (exit 2). The command writes its audit
to stdout only, with verifier/worker/inventory/environment hashes and audit time.
It does not emit replacement triples. Published selections in the nested
publication report remain the original selections.

Every output retains `usable_for_scoring=false`,
`counts_as_70_percent_evidence=false`, `outcomes_loaded=false` and zero fits.
The command is not wired into the accounting reducer or forward runner.

## Remaining activation gates

Numerical agreement does not re-establish raw API derivation, source closure,
independent pre-race availability, complete submission authority/closure,
umbrella population completeness or official target admission. Those separate
stages must follow the
[evidence boundaries](2026-10-20-condition-evidence-boundaries.md).
No automatic promotion follows this audit, and the 70% goal remains unmet.
Tests use synthetic schedules/inputs and the already stored A24/B34 models,
not another fit or an independent future-performance result.

Local validation on 2026-10-20: 43 new tests and 262 existing publication,
forward, accounting, M0 and result-observer tests passed together (305 in
40.28 seconds). Cases include actual original-code subprocess agreement,
current-parent scorer traps, changed environment, differing public prediction,
chronology, missing/corrupt evidence, extra executable files, symlinks,
one-attempt timeout, read/write/network guards and 18 forbidden fit/live
entry points. This validates the replay implementation, not a real future block.
