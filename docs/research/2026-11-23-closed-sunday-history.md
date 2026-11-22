# November 22 official individual-history supplement

The two dated official reports add 172 distinct race-and-horse
observations to the evidence already held for November 20-22. These
are historical input candidates for later research, not new accepted
labels, predictions, or results for a forward evaluation.

## Whole original card

The November 20-22 readiness card retains all 51 races and 540
declarations with its original cutoff of 2026-11-20 01:15 UTC.
The earlier 34 races and 357 linked declarations are unchanged.
The two new reports reproduce all 17 Sunday race identities and
all 183 declared gate/name joins. Stable horse IDs come from the
original API26 entries, not from a name-only candidate index.

| November 22 source | Physical races | Linked declarations |
| --- | ---: | ---: |
| [Seoul daily report](https://race.kra.co.kr/dbdata/fileDownLoad.do?fn=chollian/seoul/jungbo/rcresult/20261122dacom11.rpt&meet=1) | 11 | 117 |
| [Yeongcheon daily report](https://race.kra.co.kr/dbdata/fileDownLoad.do?fn=chollian/busan/jungbo/rcresult/20261122dacom11.rpt&meet=3) | 6 | 66 |

The southern catalogue's navigation lane is 3, but the report's
literal venue is Yeongcheon, physical venue 4. One catalogue read per
lane and one exact listed file per lane succeeded; no credentials,
API operation, retries, or additional result HTML were used. The two
file receipts ended at 2026-11-22 15:00:20.211296 and 15:00:20.565562
UTC, after midnight in Korea. These are observation times, not
certified first publication times.

| Exact original | SHA256 |
| --- | --- |
| Seoul result text | `860c8702b50afb0be302f75c1023fba522a001cb5a2b00341e2448114df32cb6` |
| Yeongcheon result text | `9a2e2dfcb10ff731fe2be478a58963c4e4835753591c6f1ca839222fd4a1150c` |

## Distinct observations and unresolved status

The 183 Sunday declarations include 180 ordinary rank/time rows, two
printed stops and one unclassified marker. At Seoul race 10 gate 4,
the timing annotation says `경주제외` and the penalty table says
`출전제외`. Keep the raw 0:00.0, blank rank and both literal markers;
do not admit a timed finish or infer an equivalence between labels.
The three source lines are 924, 938 and 1002 in the exact Seoul file.
With the separately retained Saturday marker hold, 2 of the 51 races
have this kind of unresolved interpretation; their declarations stay
in the original scope.

All 11 previously archived Yeongcheon race 4 HTML identities, ranks
and decimal times match the new text. Counting each race and stable
horse ID only once leaves 172 previously unobserved linked candidates
across 16 races in this fixed prior bank. These include unresolved or
nonordinary rows, not 172 measurements of actual starters. The text and
HTML are two formats from KRA, not the required official HTML plus
result API reconciliation. No new candidate is admitted under that
policy. The original evaluation has no new accuracy or model run.

## Similar-context coverage

Freeze the already observed 33 preliminary fields separately from
any future complete card. Count whether each has at least one prior
history candidate at the same physical venue and literal grade,
within 200 m and the previous 90 Korean calendar days. Held marker
races do not add support. No outcome from the nominations was read.

| Physical venue | Observed preliminary fields | Before | After |
| --- | ---: | ---: | ---: |
| Seoul | 7 | 3 | 5 |
| Jeju | 10 | 8 | 8 |
| Busan | 10 | 7 | 7 |
| Yeongcheon | 6 | 0 | 4 |
| Total | 33 | 18 | 24 |

This is race-context coverage, not support for every nominated horse,
a complete future population or a performance estimate. The new
observations are retained for exact source review with later
pre-deadline evidence. They do not repair the expired November input
or publication gates. Keep the unchanged M0/API27 comparison and
the separate, reviewed future whole-card requirement.

## Verification

The local `nov22-closed-history-20261123/sunday-history-evidence.json`
retains the full scope, raw source receipts, initial input pins, row
locations, distinct race/horse audit and explicit no-admission flags.
SHA256: `undefined`.
Read-only replay reproduced the identical file. A separate aggregate
check reproduced the exact previous 34 preserved race records and
the 183 / 11 / 172 linked, overlapping and additional counts. The
related local suite passed 157 tests. The [external time review](2026-11-22-external-prior-time-semantics.md)
remains valid: an external race's winning time is not an individual
horse's elapsed time.
