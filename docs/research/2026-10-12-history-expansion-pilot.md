# Historical expansion pilot: July 5-11

## Decision

Continue historical acquisition without waiting for future entry sheets. One
additional week increased prior-history coverage on the unchanged 6,816-row
archive from 58.82% to 65.07%. This is coverage, not prediction accuracy. No model
was fitted, selected, promoted, or credited toward the 70% exact-three objective.

Next acquisition priority is June 1-July 4, followed by April 13-May 31 to fill
the earliest July 12 target's 90-day lookback. Use bounded monthly batches and
the same official event/whole-roster/rank/time reconciliation. Do not treat
missing history as debut, zero starts, or a certified rest interval.

## API Diagnosis

The first July 5-11 attempt reserved three API214 requests, all timing out, and
stopped automatically. An API26 control separately failed envelope validation.
Neither observation demonstrated that historical dates were unsupported.

On October 12 at 23:30-23:31 KST, credential-safe probes returned HTTP 200 and
valid 97-row pages for July 5 Seoul from both API26 and API214 in 2.275 and 1.635
seconds respectively. The unchanged strict collector subsequently completed all
28 date/venue units. This demonstrates recovery, not a proven server root cause
or a permanent service fix. No parser was relaxed to accept error JSON as data.

`history_api_probe.py` now records fixed error categories, HTTP status, numeric
counts, timestamps and allowlisted API result codes. It persists no response
body, headers, credential-bearing URL, or exception message. Each invocation is
one request, no retries/redirects, a 45-second total deadline, and a 5 MiB decoded
body limit. A valid probe page is not a stored dataset or identity validation.

## Collection And Support

The July 5-11 pilot has 70 API race groups, 712 identity-bound runner observations,
10 nonempty date/venue units and 18 unconfirmed empty units. It used 28 new API
requests, 31 including the three failed reservations. Empty is not a no-race
certificate. The existing 128-request pilot budget was not increased.

The official support collector captured 70 detail pages and 12 list pages.
Replayed evidence confirms 50 event groups and supports 485 ranked rows. Twenty
groups remain unknown and never contribute ranked features. All 712 source rows
remain archived; they are not silently discarded or described as 712 new
training examples. Across original and extension seeds, 7,528 rows are archived
and 6,655 ranked rows are officially supported. Neither is a certified complete
national population or a historically pre-race-available training corpus.

## Fixed-Population Comparison

`history_coverage_study.py` replays all pinned raw API and official HTML evidence.
Targets are all original 671 race groups and 6,816 runner rows, unchanged before
and after expansion, including unsupported target groups. A prior event must
fall in `[target date - 90 days, target date)`; same-day and future results are
excluded. Only event/whole-roster/rank/time-supported prior observations count.

| Coverage measure | Original history | With July 5-11 | Change |
| --- | ---: | ---: | ---: |
| Target runner rows | 6,816 | 6,816 | 0 |
| Target groups | 671 | 671 | 0 |
| Rows with at least one supported prior result | 4,009 | 4,435 | +426 |
| Rows with at least three supported prior results | 469 | 630 | +161 |
| Groups where every runner has at least one prior result | 135 | 155 | +20 |
| Groups where every runner has at least three prior results | 0 | 0 | 0 |
| Rows with withheld prior observations | 546 | 919 | +373 |

For July targets, one-prior coverage rises from 9/1,210 to 132/1,210; October
targets rise only from 1,049/1,210 to 1,053/1,210. Earlier acquisition primarily
helps the left edge of the archive, as expected. The remaining 2,381 target rows
without a supported prior observation and the absence of any fully three-prior
roster argue for a longer historical window, not a more complex model yet.

Sources were downloaded after these historical races. Event-time ordering alone
does not prove information availability at the time, independent timestamps,
data finality, or complete actual starts. API and official HTML may share an
upstream system. Unsupported and unresolved prior observations remain explicit.
Existing approved API27/M0 training and forward prediction inputs are untouched.

## Reproduction

From repository root, with the existing Python environment and ignored local
archives present:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.history_coverage_study \
  --root .cache/autoresearch/observed-history-20261011 \
  --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
  --seed-sha256 0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66 \
  --archive-dir .cache/autoresearch/official-history-20261012-v2 \
  --archive-sha256 eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2 \
  --history-source .cache/autoresearch/observed-history-extension-20260705-11 \
    .cache/autoresearch/observed-history-extension-20260705-11/seed-final.json \
    8892efdc45e910cec965e13f498042cf2132e9fed0ebdabf8b590010c38ffa81 \
    .cache/autoresearch/official-history-extension-20260705-11 \
    8f636085beff392bcb93b913dd6e8014752ccd68de625be7a09040d283e2b7f1 \
  --output .cache/autoresearch/history-coverage-20261012/replay.json
```

Do not overwrite existing output. The executed `expanded.json` has SHA256
`724d0427aaf35b3da2a247faf1bbb10d6b99f49decab93f0155e076742818620`.
Raw archives and credentials are excluded from Git. Probe receipts are in
`.cache/autoresearch/history-api-diagnostics/`; initial and final collection
attempts are retained separately in the extension seed directory.

## Validation And Remaining Work

Twenty-five new tests cover error/empty separation, secret-bearing responses,
timeouts, redirects, response limits, strict prior-date boundaries, fixed target
membership, unsupported history, duplicate source rejection and raw tampering.
The combined new/history/M0/API27 regression run passed 163 tests. Ruff check,
format check and diff whitespace checks pass. Scripts CI runs the new tests.

No new ChatGPT Pro consultation occurred in this increment: access recovered
and the existing strict support method was sufficient. Consult Pro before a
materially different reconstruction/training policy; do not infer authorization
from today's historical downloads. Paid services remain deferred.

The goal service still reports `blocked`; the exposed goal tools cannot resume
it and native Codex UI control is unavailable. Research itself has resumed, and
future entry-sheet absence must not be treated as a block on historical work.
