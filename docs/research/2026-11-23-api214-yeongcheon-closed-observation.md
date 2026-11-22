# One observed return from the existing API214 result route

On November 23 KST, the installed JSON API214 route returned a
normal response for the completed November 22 Yeongcheon meeting.
The six races and all 66 declarations link to the retained original
entry keys. Only race 4 meets the comparison with existing detailed
HTML. This is one post-race source observation, not proof of
service-wide recovery, a scoring run, or a training admission.

## Fixed request and evidence

Re-use the original 51 races and 540 declarations in the
[closed Sunday archive](2026-11-23-closed-sunday-history.md).
The original first cutoff stays `2026-11-20T01:15:00Z`. The
11/22 Yeongcheon scope (physical meet 4) is closed and has 6 races
with 11 declarations each. The one API request was prelimited to
that previously unqueried date/venue, page 1, size 100, JSON:

`https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1`

Observed HTTP 200 / provider code `00` with totalCount 66, exactly
one page and no follow-up, redirect, retry, new schedule or HTML
request. The request completed at `2026-11-22T20:44:04.477009Z`.
The three prior November attempts with no response headers remain
unchanged. This result does not explain their failure or verify
current remaining quota, other routes, or repeat availability.

| Preserved observation | SHA256 |
| --- | --- |
| API214 original response, 94,894 bytes | `fe87abbc999e125a6f6e95af2c9dd6f4a038aec9acc91151583f5d20f0145df5` |
| Original capture manifest | `cb55e7f44956fda57c1c3d1150ec5db2ee3625a226f1679be0c48e8c8e6202b8` |
| Replayed comparison and single-request receipt | `5644507f10810ae19273de904a0ca7982bacd221361a93f43581944a720ee83e` |
| Earlier Yeongcheon daily report | `9a2e2dfcb10ff731fe2be478a58963c4e4835753591c6f1ca839222fd4a1150c` |
| Earlier race 4 detail HTML | `e82a9c5235735b43b80e56a2d4b004dae94cf75508c3586922d057e64440a2b4` |

The API body has no physical `meet` key on any of its 66 rows.
The original API capture therefore remains `identity_unresolved`.
The existing full-day identity binder links the exact complete
dated race, saddlecloth and horse-ID set to the retained API26
declarations (no added or missing keys). The observation ledger
labels all rows as `api26_full_day_roster` venue evidence, not
as venue values returned by API214. The request's meet argument
alone is not identity evidence.

## Two distinct comparisons

| Observation | Coverage | Outcome |
| --- | ---: | --- |
| API214 plus the daily result report | 6 races / 66 rows | All 66 ordinary ranks and elapsed times agree |
| API214 plus the existing race 4 detail HTML | 1 race / 11 rows | Existing policy reports `unique_top3_observed` |

A separate Ruby check reads the raw JSON, independently joins the
66 exact report keys and compares decimal elapsed seconds and
ranks. The five other races have no selected detailed HTML, so
their daily-report agreements do not pass the existing result
policy. In the unchanged 51-race source ledger, 1 is
`unique_top3_observed` and 50 remain `source_missing` (five
missing detail and 45 without an API result in this observation).
Missing is not an incorrect forecast or proof of no race. The
observation does not resolve result finality or settlement rules.

The private `api214-yeongcheon-closed-scope-20261123/actual`
archive retains the source, exact original bytes, clocks, request
reservation, missingness and separate result-policy states.
`result_probe.py verify` reproduces the receipt without a request.
The four offline probe tests and 229 existing regression tests
passed; the same scope now reports its attempt as consumed.

Neither the elapsed cutoff nor any prediction can be restored
by this later outcome. No training target was admitted, no model
changed, and no full or partial accuracy was calculated. The 102
results pending in the earlier November research remain separate.
Preserve the next actually published whole card and its input
versions before its original cutoff, independently of result-channel
availability. No dates or future evaluation populations are set here.
