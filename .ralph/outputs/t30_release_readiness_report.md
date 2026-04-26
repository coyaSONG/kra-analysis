# T-30 Release Readiness Report

Verdict: **BLOCKED**

## Blocking Reasons

- DB replay produced zero T-30 strict rows for the fixed mini_val/holdout manifests.
- Existing snapshot artifacts do not contain `operational_cutoff_status`, so the freshness gate fails for all holdout races.
- Existing artifacts have 0% coverage for `recent_*`, `cancelled_count`, and `field_size_live`; `weight_delta` coverage is 93.5%.

## DB Replay

- mini_val requested 200, written 0, failures 200.
- holdout requested 500, written 0, failures 500.
- failure reasons: `{"mini_val": {"late_snapshot_unusable": 200}, "holdout": {"late_snapshot_unusable": 375, "partial_snapshot": 125}}`

## Existing Snapshot Probe

This probe is not release-valid because freshness metadata is missing, but it shows the current artifact weakness.

- baseline exact 3-of-3: 0.386
- release feature exact 3-of-3: 0.382
- exact delta: -0.004
- avg set-match delta: -0.001

## Next Actions

1. Collect or reconstruct entry-finalized snapshots before T-30 for the holdout race ids.
2. Persist `entry_change_bulletin` snapshots with `source_snapshot_at`.
3. Rerun offline dataset replay with `--with-past-stats` once strict snapshots exist.
