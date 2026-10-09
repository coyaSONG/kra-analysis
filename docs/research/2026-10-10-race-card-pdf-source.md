# Pre-race PDF source contract and capture evidence

This research increment adds a source, not a new prediction model. The target remains a 70% exact unordered single-three-horse prediction rate across the complete frozen race universe. No accuracy evaluation or model promotion occurred here.

## Source and Intended Use

Official KRA race cards list current-horse training counts/minutes, recent gate training, swimming, trainer statistics, and recent listed treatments, including some horses with no racing history. The observation grain is one horse in one race: `(meet, race_date, race_no, chulNo)`, joined to the complete API26 entry sheet by runner number and full normalized horse name. The persistent horse ID comes from the API, never from a guessed PDF identifier.

The official URL patterns are `https://race.kra.co.kr/down/pdf/{directory}/chulma/{prefix}_run_hr_{YYMMDD}_{NN}.pdf`, where `(meet, directory, prefix)` is `(1, seoul, s)`, `(2, jeju, j)`, or `(3, busan, b)`. The current increment does not support a meeting-4 PDF layout. API26's pre-race entry service is documented at the [official public-data portal](https://www.data.go.kr/data/15058677/openapi.do). Text extraction uses the [pdfplumber bounding-box APIs](https://github.com/jsvine/pdfplumber) and validates the known A4 layouts and each page's meeting/date/race footer.

Only the first two current-horse columns are inspected. The historical results table is excluded. Treatment entries are recent printed records, not an exhaustive clinical history; no printed treatment does not mean no disease. Seoul/Busan training summaries have no explicit window duration in the extracted label. Jeju explicitly prints a two-week window. Do not assume these are identical measurement windows.

## Availability and Identity Guards

Original PDF and successful API page bytes are saved with SHA-256 checksums in separate, timestamped acquisition directories. Actual timezone-aware acquisition completion is the timing evidence. Server Date, Last-Modified, or ETag headers cannot make a retrospective download pre-race-safe. These are local observations, not cryptographically attested third-party timestamps.

Both PDF and entry captures must complete no later than the scheduled start minus 30 minutes. The PDF start time, API entry start time, and supplied schedule must agree. All official runners must match one-to-one by number and full name; duplicate runners, duplicate provided horse IDs, missing runners, unsupported layouts, future event dates, missing timestamps, and mismatches block the whole race. No partial-join horse subset is emitted on failure.

Missing numeric values remain null; an explicit printed zero remains zero. If a rider list overflows the panel boundary, only the complete training count/minutes prefix is retained, with `training_summary_truncated: true`; rider names and absent suffix counts are not guessed. JSON manifests record field evidence and bounding boxes. No current-race result is extracted.

API26's `rc_no` filter was not honored in the observed response. The collector reads all pages, checks page sizes and stable total count, then filters response meeting/date/race itself. It validates declared field size and schedule consistency. Numeric horse IDs become strings without invented padding, while leading zeroes in string IDs are preserved. Credentials and authenticated URLs are never saved; HTTP error strings are sanitized.

## Usage

Run from the repository root:

```sh
uv sync --package kra-scripts --extra race-card-pdf --group dev --inexact
.venv/bin/python packages/scripts/autoresearch/kra_race_card_pdf_snapshot.py \
  --meet 1 --race-date 20261010 --race-no 1 --fetch-entries --require-eligible
```

Automatic entry capture reads `KRA_API_KEY`, `--api-key-file`, or the owner's existing `~/.codex/secrets/kra_api_key`. Do not place a real key in a committed file or command argument. `--entries path/to/entries.json` can replace `--fetch-entries`; that file must have the following envelope, with actual acquisition time rather than a reconstructed date:

```json
{
  "meet": 1,
  "race_date": "20261010",
  "race_no": 1,
  "collected_at": "2026-10-09T15:38:27.131771+00:00",
  "scheduled_start_time": "1035",
  "entries": [
    {"chulNo": 1, "hrName": "FULL_OFFICIAL_NAME", "hrNo": "OFFICIAL_ID"}
  ]
}
```

The example is a schema illustration, not a complete real race. Exit 0 means capture and parsing succeeded, not necessarily eligibility. With `--require-eligible`, a blocked attempt returns 2. A fetch or parse failure returns 1. Every attempt has its own manifest; earlier observations are not overwritten.

## Observed Cohort

Actual PDF captures completed on October 10, 2026, 00:42:01-00:42:41 KST, before the recorded deadlines. The local cohort manifest is `.cache/autoresearch/race_card_pdf_snapshots/cohort_20261010_11_capture.json`, with SHA-256 `c0e7ff433484652753e2207b3005dd783186280b204519f63cdf1c844962576c`. It references the exact raw hashes, per-race manifests, parsed counts, audit reasons, and numeric coverage. Downloaded PDFs and raw API pages remain in ignored local cache, not in Git.

| Meeting / Date | Captured Races | Entry Horses | Eligible Races |
| --- | ---: | ---: | ---: |
| Seoul / 2026-10-10 | 10 | 108 | 10 |
| Jeju / 2026-10-10 | 7 | 65 | 7 |
| Seoul / 2026-10-11 | 11 | 121 | 10 |
| Total Captured | 28 | 294 | 27 |

All 28 PDFs parse and match the requested document identity. Training counts/minutes are available for 294/294 horses; six rider summaries are marked truncated. Gate dates are printed for 236/294 horses, and recent treatment entries for 278/294. Among the 229 Seoul horses, swimming counts are available for 228 and trainer wins/rates for 218. Jeju does not print those swimming or trainer-statistic fields in the inspected template; its 65 missing values are structural, not zeros. No long-term drift conclusion is possible from this two-date capture.

Strict source eligibility is 27/28 captured races (96.43%) and 282/294 horses (95.92%). These are data coverage metrics, not prediction rates or nationwide coverage. The October 11 Busan API request returned totalCount 0; that meeting/date's race universe remains unknown and is separately recorded, not silently removed from a model evaluation denominator.

## Unresolved Findings

Seoul October 11 race 8 is blocked despite matching all 12 runner numbers. Nine PDF names use the regional prefix Bu (`[\ubd80]`) while API names use Yeongnam (`[\uc601\ub0a8]`); the remaining name text matches. This is a high-confidence source inconsistency and a high-priority identity-join risk, not permission to strip arbitrary prefixes. All feature rows for the race remain withheld until an authoritative, race-local alias rule is verified and tested. Model evaluation must retain the race and use a preregistered fallback rather than excluding it.

Trainer summaries sometimes overlap printed text and one swimming line is not recognized. Their localized missing values remain explicit. Bounding-box extraction intentionally favors missing data over using adjacent historical columns. A changed page size, missing separators, wrong footer, or unsupported layout blocks the source.

Before a model consumes this cache, recheck raw checksums, source manifests, exact parser implementation/version, and entry provenance. A manually supplied JSON timestamp is not independent proof of acquisition. A fresh cutoff capture is also needed to detect later scratches or entry changes. Current captures do not establish correctness of those later updates.

## Verification and Next Research Gate

The focused suite currently passes 110 tests, including generated real-PDF round trips for all three meetings, two-digit joined headers, pagination, numeric IDs, duplicate/missing joins, actual completion-time cutoffs, retrospective capture rejection, credential-safe errors, and CLI failure precedence. Dedicated CI installs the optional extra so the PDF cases cannot be silently skipped through absent dependencies.

The clean integration branch updates anyio/cryptography/urllib3 to 4.14.2/50.0.2/2.8.0 and the solver-required MLflow family to 3.17.0. The PDF capture dependency closure passes pip-audit with no known findings. All 28 cached raw-PDF replays match the original parsed/audited output; 35 API auth tests pass (two existing skips), RSA/JWT round-trip smoke passes, and the MLflow wrapper passes isolated SQLite tracking. The original research branch's older environment was not overwritten. A broad workspace audit still reports existing findings in 13 other packages, and main CI already fails its security job; those findings are not suppressed or claimed fixed. Require the normal protected-branch Python status and the dedicated PDF check before merging this increment, without an admin override.

```sh
.venv/bin/python -m pytest -q \
  packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py \
  packages/scripts/autoresearch/tests/test_kra_race_card_pdf.py \
  packages/scripts/autoresearch/tests/test_kra_race_card_pdf_audit.py \
  packages/scripts/autoresearch/tests/test_kra_race_card_pdf_snapshot.py
uv lock --check
```

Next, lock a complete future race universe, one baseline model, and a limited predeclared training-feature ablation before observing outcomes. Compare the same single three-horse metric on identical races, preserve missing-source fallbacks, and evaluate uncertainty at the race/date level rather than treating horse rows as independent trials. The spent December 2025 holdout is not reusable for selection. These captures are a prospective feature archive, not an already executed prediction holdout.

For difficult design questions, the owner requires ChatGPT Pro advice through the browser and waiting for the completed answer without short response timeouts or stopping generation. In this session the in-app browser was unavailable and Chrome was logged out; a login handoff was requested. No Pro consultation is claimed. Goal automatic continuation also remains paused until the owner resumes it. Manual work in this turn is separate from that status.

Implementation is merged into main through [PR #55](https://github.com/coyaSONG/kra-analysis/pull/55), commit `ae9207f`. Required Python CI and the dedicated PDF suite pass, as do scripts, Docker, and secret scanning. The broader dependency audit still has its documented pre-existing failures. The owner still has the unrelated research working-tree changes; they were not merged or reverted by this increment.
