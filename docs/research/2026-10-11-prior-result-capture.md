# Official result observations: October 9-11, 2026

## Result and Limits

The six selected API214 venue/day captures contain 510 rows for all 50 race IDs in the retained dated official schedule. No race is missing or extra. There are 487 ranked-finish observations and 23 unresolved rows. Nine races have one more result row than the schedule runner count, so population reconciliation remains **false** and the audit exits 2. This is source research, not a performance evaluation or a future frozen universe.

No model, `rest_days`, `rest_risk`, training approval or production database was changed. The target remains one unordered three-horse prediction per race, pre-race inputs only, exact success of 70% across the entire frozen universe. Historical captures made today cannot establish acquisition before 2025 cutoffs. Complete pagination does not establish complete actual-start history or atomic server-side snapshots.

| Date | Physical venue | Races | Rows | Ranked finish | Unresolved |
| --- | --- | ---: | ---: | ---: | ---: |
| 2026-10-09 | Jeju (2) | 7 | 61 | 60 | 1 |
| 2026-10-09 | Busan (3) | 9 | 92 | 90 | 2 |
| 2026-10-10 | Seoul (1) | 10 | 108 | 95 | 13 |
| 2026-10-10 | Jeju (2) | 7 | 65 | 64 | 1 |
| 2026-10-11 | Seoul (1) | 11 | 121 | 118 | 3 |
| 2026-10-11 | Yeongcheon (4) | 6 | 63 | 60 | 3 |

Observed raw pairs, **not a universal API code contract**, are 92 / 주행중지 (3), 94 / 경주제외 (7), 95 / 출전취소 (2), and 98 / 경주불성립 (11). All 11 rows in Seoul October 10 race 1 have the latter status and remain in the ledger. Their positive win odds also demonstrate why positive odds must not be used to prove a valid finish.

Count mismatches are `20261009_2_2`, `20261009_3_9`, `20261010_1_7`, `20261010_2_2`, `20261011_1_3`, `20261011_1_9`, `20261011_1_10`, `20261011_4_4`, and `20261011_4_5`. Each contains one exclusion/cancellation note. This supports a possible active-versus-listed population explanation, but no row was removed to force equality and no broad status mapping was approved.

## Identity Discovery

Every one of the 63 Yeongcheon result rows lacks `meet`. The initial failed capture remains immutable. A subsequent capture reports `identity_unresolved`, and standalone replay rejects it. A separately retained API26 response explicitly identifies Yeongcheon and matches all 63 `(date, race, gate, stable horse ID)` tuples in both directions, including every race in the day. Replay can bind venue using this evidence, preserving `raw_meet=null` and `venue_identity_basis=api26_full_day_roster`.

API26 race 4 contains 10 rows but declares 9; race 5 contains 11 but declares 10. The pre-race entry projection correctly rejects those fields. The shared replay extraction verifies raw page provenance independently; it does not weaken the existing pre-race complete-roster checks or add unsupported PDF venues. Combined source availability is no earlier than the later capture completion, 2026-10-11T11:08:52.883933+00:00. Local acquisition timestamps still lack independent server attestation.

## Completed Pro Consultation

The user's selected ChatGPT Pro completed the follow-up after **13m 56s**; generation was not stopped and partial output was not used as final advice. Questions covered API status semantics, finite lookback coverage, PDF history, and the smallest operational next step. Key accepted design recommendations:

- Keep website status definitions separate from an unverified API214 ordinal contract.
- A newer unknown event or coverage gap prevents an exact last-start value; the gap from the last confirmed start can be an upper bound, not the exact interval. An older unknown event need not invalidate a later confirmed date when the subsequent interval is complete.
- Preserve official race participation separately from physical exercise, and exclude trial events only through explicit event-kind evidence. PDF history can mix trials and races.
- Do not inject new values into existing trained feature columns. Use a new semantic version and train/serve contract when evidence permits.
- **Next implementation priority: connect PR68 to the actual PostgreSQL B0 submission/commit-observation path.** Research history is not a consumed B0 input and must not delay submission.

Primary-source checks independently repeated after the advice:

- The [API214 catalog](https://www.data.go.kr/data/15063979/openapi.do) lists results, status notes and elapsed race records, includes physical venue 4, and links an API214 document. The complete ordinal contract was not obtained; no mapping was invented.
- The [KRA disposition guide](https://race.kra.co.kr/raceguide/RaceTakePartHorseCancleService.do?Act=06&Sub=3&meet=1) distinguishes cancellation/exclusion from stopping during a constituted race.
- The [August 12, 2018 Seoul race 8 official report](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=1&realRcDate=20180812&realRcNo=8) describes runner 6 starting and later stopping near the finish despite an absent finish record. This refutes a finish-only last-start filter; it is not yet an API214/hrNo-joined classification fixture.

The B0/PostgreSQL path remains **unfinished**. This PR is a source-capture increment, not completion of Pro's broader operational recommendation. The next work should implement real PostgreSQL tests and the submission path rather than expand diagnostic registries or another broad historical search.

## Reproduction and Pins

Run from the isolated repository root with `PYTHONPATH=packages/scripts`. Capture uses `python -m autoresearch.kra_result_snapshot capture --meet M --race-date YYYYMMDD --api-key-file PATH --output-dir DIR`; audit accepts `--capture` and optional `--entry-capture` / `--archive-root`. Secrets are never command arguments or manifest fields. A capture stores complete safe original bytes before parsing, rejects credential echoes, and uses unique immutable directories.

The population plan is explicit and hash-pinned, not a glob that might include retry duplicates:

```json
{
  "format_version": "kra-result-population-plan-v1",
  "race_dates": ["20261009", "20261010", "20261011"],
  "archive_root": ".",
  "schedule_capture": "path/to/schedule/capture.json",
  "schedule_sha256": "<64 hex>",
  "result_captures": [
    {"path": "path/to/result/capture.json", "sha256": "<64 hex>"},
    {"path": "path/to/venue-missing/capture.json", "sha256": "<64 hex>",
     "entry_capture": "path/to/entry_capture.json", "entry_sha256": "<64 hex>"}
  ]
}
```

Paths are interpreted from the invocation directory; API26 archive references must stay under `archive_root`. Run `python -m autoresearch.kra_result_population_audit --plan PLAN --output NEW_REPORT`. Existing outputs are never replaced. Failed sources remain explicit, while the schedule is always the left side of the race ledger.

Actual ignored artifacts under `.cache/autoresearch/`:

- Schedule: `forward-schedule/20261011T100723.518882Z_a349dc8395f0/capture.json`, SHA-256 `08fe1bb58be2a394476158e8a52697a2ae2e77c9e1bf6084b1e11972fae3a7c7`.
- Plan: `prior-results/population-plan.json`, SHA-256 `4c3385228e1f80d5a0cd609d9a78b236e3a3d53efdc8676920276039455cfb03`.
- Report: `prior-results/population-audit-v2.json`, SHA-256 `2f71e5e16951f20b503d9028175e0f814259594eaf9a6d926cb9158d0eae2aa0`.
- API26 binding: `prior-results-entry-crosscheck/20261011_4_1/entries_20261011T110428.897097Z_9b6a961257f9/entry_capture.json`, SHA-256 `d42dd1fcc5d226e6580763196354df8ef921d295e722d6078346bf5d6b23bbf5`.

The result manifest paths below are relative to `.cache/autoresearch/prior-results/`; each manifest pins all original pages and the report preserves those page digests.

| Capture manifest | SHA-256 |
| --- | --- |
| `20261009_2_20261011T110354.721014Z_e61a2b199eca/capture.json` | `254f0c666d647deb27cd1c2c9bf86c0bb59c9aac154124f2dc001d8f047f0b5f` |
| `20261009_3_20261011T110356.949552Z_729e41b7bfa8/capture.json` | `0e45dafcca04842d15bb8d6ade0a366e04af310dacc96ac7e0ec3f1f7f70ecea` |
| `20261010_1_20261011T110408.138627Z_8513d20fcd2d/capture.json` | `42856e3b732d456b8d62b773af114c1e5f6527369f7a784f534d6be9a7f1aa8d` |
| `20261010_2_20261011T110410.680623Z_2c6782e5b556/capture.json` | `45af496eb851c1b5e8d130b3e50badacd7eee0a5ab178f4164c9bdc051f02b03` |
| `20261011_1_20261011T110235.633772Z_51e1a7211f73/capture.json` | `baebabf16402cbaf393d2a3594ba68860b6a2ad1a3bce723169902652d2d24da` |
| `20261011_4_20261011T110852.651188Z_b0e08d316781/capture.json` | `67ef9747670fae540b8d615b1f5d9f98a6b490725dbb19148983036e1b784d4f` |

## Verification

Focused source/replay/bundle tests: 130 passed. Expanded training-evidence, schedule, paired diagnostic, entry interval, entry collection and all PDF regressions: **410 passed**, with 15 existing joblib/NumPy deprecation warnings. Ruff lint/format and diff checks passed. Two actual population replays were byte-identical. Tests cover whole pagination, preserved failures, credentials, strict JSON, identity conflicts, missing venue binding, later availability, unchanged pre-race roster rejection, pinned plan replay, failed-source left joins, void races and non-overwrite output. CI outcomes are recorded in the PR. Synthetic tests do not certify official status semantics, true historical completeness, independent timestamps or predictive improvement.
