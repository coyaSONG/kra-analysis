# API only training opportunity

## Finding

The original October 10-11 archive supports **27 API-only training candidates
with 283 runner rows**, compared with the existing approved 20-race, 209-row
PDF/API training cohort. This adds seven candidate races and 74 rows without
collecting retrospective replacement inputs. No new training is approved or
performed here. The frozen M0 model and October 16-18 evaluation contract remain
unchanged. This is not an accuracy gain or a replacement evaluation denominator.

All 28 original races and 294 runners remain in the inventory. The one noncandidate,
`20261010_1_1`, has a versioned void observation and no defined top three; its 11
input rows are preserved rather than relabeled as negatives.

## Source and label checks

The original plan and bundle were publicly committed by PR61 before the original
captured T-30 cutoffs. T-30 means 30 minutes before the scheduled start recorded
in the pre-race source, not a later result-page time. The replay re-fetched GitHub
metadata at `2026-10-11T20:33:57.870527Z` and verified the original merge time
`2026-10-09T17:08:16Z`, commit `f794ffc24414117420004ca45bd8ae20a04385db`.
GitHub establishes a content-existence bound, not independent authentication of
KRA's source contents or registration of predictions.

All 28 API26 raw source chains replay. Each input roster matches the complete
observed output roster by gate and canonical horse ID. The projection uses only
seven original API fields and seven missing flags. The unique top-three labels
come from the fixed PR83 API214/official-HTML observation policy, replayed from
raw frozen sources. Final settlement status remains unverified.

| Additional candidate | Why the old cohort excluded it |
| --- | --- |
| `20261010_1_6` | Lower-rank completeness condition |
| `20261010_1_7` | Lower-rank completeness condition |
| `20261010_2_2` | Lower-rank completeness condition |
| `20261011_1_10` | Lower-rank completeness condition |
| `20261011_1_3` | Lower-rank completeness condition |
| `20261011_1_9` | Lower-rank completeness condition |
| `20261011_1_8` | PDF name join, not the API-only roster |

For the first six, the newer cross-source observation policy confirms unique
ranks 1, 2 and 3 despite lower-rank exceptions. The PDF problem in the seventh
is not used to approve PDF features. No excluded PDF rows are fabricated.

## Reproduction

From the isolated research checkout, run:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.api_training_opportunity \
  --plan .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/input_plan.json \
  --bundle .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json \
  --archive-root /Users/coyasong/Developer/coyasong/kra-analysis \
  --outcome-plan .cache/autoresearch/versioned-outcomes-20261012-plan.json \
  --output-dir .cache/autoresearch/api-training-opportunity
```

The archive is local and ignored by Git; the command requires the existing raw
files. It writes a new timestamped directory, never overwrites the old cohort,
and fails on changed input or outcome-policy hashes. No credentials are emitted.
It is an investigative replay, not a training admission API.

The actual report is
`.cache/autoresearch/api-training-opportunity/20261011T203357.256735Z_9adf31083036/report.json`,
SHA256 `0cd394cb786f0e2cb17988746e92a49860236e9c8069d84d32a9e94eba61ae67`.
All 28 race records, 294 feature rows, labels, source pins, cutoffs and additional
candidate memberships match the prior independent exploratory projection,
SHA256 `04359e468e1ef3b1836ebc06fe2cc86eaea52319b3429b5d4a48fbf17fa8c6a1`.

Input plan SHA256: `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`.
Bundle SHA256: `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
Outcome plan SHA256: `314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898`.
Outcome policy SHA256: `389f4cffa53f5e7172383aa9e452fd53cf8afeb6091a4728379cb8b2e8a3bd28`.
Outcome dependency map SHA256: `2d9f1a7aeb847048c371408aad35ac52b170526a0871acaec21fcba538d1bb3c`.

The new 22 policy/projection tests plus existing outcome, M0 forward/evaluation
and source-witness regressions passed: **130 tests**. Static lint passed.
Tests reject late publication, capture after publication, incomplete or mismatched
rosters, invalid top-three sets and unproven source chains while preserving
noncandidate rows. The initial test invocation used a nonexistent inference
test filename; no tests ran in that attempt. The corrected suite above passed.

## Bounded June audit

Three normalized API26 files and two archived HTML capture directories were
examined in the read-only primary checkout. This is not an exhaustive search of
every historical cache and does not establish that no other evidence exists.

| Target date | Normalized races / rows | Timing and roster finding |
| --- | --- | --- |
| June 26 | 9 / 86 | All file-generation times after declared T-30 |
| June 27 | 17 / 179 | Generation before declared T-30, raw response chain missing |
| June 28 | 10 / 105 | Nine schema-valid races generated before T-30; Seoul R7 has 9 entries versus declared 8 |

These files contain transformed entries and endpoint summaries, not original
HTTP response pages. The old collector applies date defaults and duplicate
suppression. A file-generation timestamp alone cannot prove that the transformed
feature values existed before the race. No historical independent hash publication
was found within this bounded check. None is approved for training.

The June 27 and 28 HTML directories each contain eight saved UTF-8 bodies and
sidecars. All 16 body hashes and byte counts match. Parsed tables contain
schedules, lists or explanatory material, with no complete individual-horse
roster. A schedule race-ID join is not a join proving horse-level features.
The saved bytes are decoded/re-encoded text, not necessarily original wire bytes.

The corrected diagnostic is
`.cache/autoresearch/legacy-source-inventory-20261012-v2.json`, SHA256
`9cc9c5a5e866259edd611e3c8fabc1da84c646c230b421e329c8cf31d0eb3c94`.
It supersedes an initial diagnostic that incorrectly expected HH:MM instead of
the API's HHMM schedule format. No underlying source files were changed.

## Completed Pro advice and next decision

The authorized [Pro strategy consultation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
completed with the UI showing **11m 56s** processing time and an explicit completed
status. Generation was not stopped, restarted or used as partial advice. Pro read
public PR85 code, not local raw files or tests. Its request preceded discovery of
the seven additional October candidates, so this is **not an external review or
approval of those seven races or this new code**.

Pro recommends ending the bounded June audit and prioritizing real future
training inputs: the existing API26 14 columns plus PR85's five recency values
and their five missing flags, 24 columns total. Keep the selected history version
fixed for the week, preserve all national study members, read M0's selected raw
API26 snapshot, and seal the first eligible input packet per race without
replacing any M0 prediction. Missing history stays null with coverage metadata;
it does not remove a runner or race. Labels attach later in a separate versioned
sidecar. Models trained on those labels can only be evaluated on a later period.

Adopt that future-input adapter as the next implementation priority. Its immediate
acceptance is one nonempty historical raw replay proving the connection, clearly
rejected as future/PIT evidence, followed by real prospective packets when the
cards appear. Its research completion requires actual future national membership,
input packets or explicit failures, source chains and timely public hash evidence.
An empty registry, historical replay, or extra tests alone does not meet that
research completion condition. No additional history collection or feature search
is needed for this first 24-column version.

Do not retune on the already observed development races or call the seven extra
races a fresh holdout. A separately reviewed fixed API-only refit on the 27-race
candidate corpus remains possible, but it needs exact source, label-version,
feature and recipe approval and must not replace frozen M0 implicitly. The June
audit is closed unless a concrete new pre-race source receipt appears. Reported
UTC timestamps are not KST calendar dates: June27 JSON generation was at
June27 01:23:21 KST, not the previous Korean calendar day.

The actual future-card refresh at `2026-10-11T20:24:01Z` still found October 16,
17 and 18 awaiting cards. No prediction or success rate was generated. Paid
server provisioning remains deferred under the owner's instruction.
