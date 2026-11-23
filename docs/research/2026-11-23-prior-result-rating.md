# Rating differences from already archived comparable starts

An older result rating adds a distinct observed value for 321 November
declarations that lack the existing entry-to-entry rating difference.
This is coverage, not predictive lift: only 2 of 153 original races have
this difference for every declaration. Never use a current race's result
rating to reconstruct its pre-race inputs.

## Same-start source and missing-value check

The [2026 KRA racing plan](https://race.kra.co.kr/down/raceplan2026_20260516.pdf)
describes result-informed rating review and weekly publication after Sunday
racing. It does not label the clock or edition of an individual raw rating
cell. The [API227 catalogue](https://www.data.go.kr/data/15089492/openapi.do)
describes a rating column in historical results. This audit does not call
that operation: its actual sources are already retained API214 responses,
official result detail HTML and the original API26 entry responses.

Match the exact race ID, program number and stable horse ID in all three
formats for the original October 16-18 card. The 534 declarations and
both result rosters are equal across all 50 races. Use only rating and
identity fields in this control. The [PR #95 entry witness](https://github.com/coyaSONG/kra-analysis/pull/95)
precedes the original cutoff. The preserved result bytes and their
[PR #108 report witness](https://github.com/coyaSONG/kra-analysis/pull/108)
come after it. The two result displays are from the same publisher.

| Original API26 state | Declarations | API214 result | Official result detail |
| --- | ---: | --- | --- |
| Positive | 392 | Same positive value | Same positive value |
| Numeric zero | 110 | Numeric zero | Blank |
| Null or missing | 32 | Numeric zero | Blank |

There is no positive mismatch in this preserved edition. This does not
establish universal equality, the original provider release time, or
which edits the result fields may receive later. It also shows that these
result displays cannot recover the original distinction between missing
and literal zero. A result-only substitute would corrupt that distinction
even in this matched card.

## Earlier rating reach on the three original November cards

Keep the exact latest earlier start already chosen in the
[same-start comparison](2026-11-23-matched-prior-price.md), before
inspecting any rating. It is the latest eligible start in the archived
bank, not evidence of the horse's actual last start. It must match the
same horse, physical venue and literal class, be within 200 m and 1-90
calendar days earlier, and have source and witness evidence strictly
before the original entry receipt. A missing or ambiguous latest record
is not replaced by an older one. Verify both historical source rosters
and require the same positive rating in API214 and official HTML. When
the current API26 rating is also positive, subtract the earlier rating
from it. Keep a measured difference of zero distinct from no difference
available. This is not a single official adjustment or its causal effect.

| Original card start (KST) | Races | Declarations | Earlier result rating difference | Not reached by the older entry comparison | Full fields |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nov 6 | 51 | 496 | 212 | 144 | 0 |
| Nov 13 | 51 | 513 | 213 | 100 | 1 |
| Nov 20 | 51 | 540 | 213 | 77 | 1 |
| Total | 153 | 1,549 | 638 | 321 | 2 |

The entry-to-entry comparison has its own weight-rule match, uses locally
observed earlier entry versions, and reaches 403 declarations. This is
an overlap description, not interchangeable source coverage. There are
also 80 rating differences outside the 803 earlier finish/price pairs;
58 have neither an entry-to-entry difference nor a finish/price pair.
Of the 911 without a
new rating difference, 642 have no eligible earlier comparable start and
269 have a zero/blank earlier result rating. Do not use a result zero as
a rated observation.

By physical venue, support is Seoul 273/654, Jeju 209/403, Busan 81/319
and Yeongcheon 75/173. The difference distinguishes 95 pairs with the same
current positive rating in 51 races, with overlapping runners and fields.
That comparison does not account for all other existing predictors. The
original three November entry clocks are local checks, not independently
timed inputs or predictions for a new study.

## A separate source for unrated fields

All 426 declarations in the 41 domestic/Jeju class-six races lack a
positive current rating. On the original November 20-22 card alone,
all 14 such whole fields have at least one earlier printed practice date:
80 of 149 declarations, but no field with every runner covered. On the
independently witnessed October PDF card, the 13 wholly unrated fields
have 132 such dates for 140 declarations; six fields are complete. This
readback rejoins the exact retained
[practice inventory](2026-11-23-gate-training-source.md), retains only
printed days before the PDF receipt date, and never fills in a same-day
event time. The November PDF is local only. These two source comparisons
do not estimate future practice coverage or skill.

## Research decision

Retain one optional candidate difference plus a separate missing state
for a later same-base comparison. Fix the context, source edition and
missing policy before any training. The unrated fields warrant separate
priority for an independently timed practice or trial input, without
dropping the field or substituting an invented rating. First protect the
next entire official card and the original fixed M0/API27 workflow. A
selected candidate would need admitted frozen training cards and a
different, pre-enrolled complete future evaluation using the original
one-unordered-trio target. The October control and November coverage are
not that validation.

## Reproduction

The private archive `.cache/autoresearch/prior-result-rating-20261123/`
stores the immutable runner ledger `prior-result-rating.json` (SHA256
`336eb1fa88f5adce7f89ee23a4840d60e38b1f4fa9f892b76e798e0376c1f298`),
the exact source pins and clocks, and distance/class/venue missingness.
`readback.py verify` replays the existing sources without writes or requests.
Its SHA256 is `398dff86f8793aaf4418af5f70287e546ab39efae22e4c05a09b2eb226dbdb6b`.
A separate Ruby calculation rehashed the API pages and both official
references for 304 past result fields and independently reproduced the
392/638 counts, two full fields and the 95 within-rating pairs.
`gate_overlap.jq` repeats the two exact PDF joins; the canonical output
SHA256 is `8755d59d8f7a0cd01140d9ba87a98c47bf9a0dba0dc663dcafc225735aebde38`.

From the isolated checkout with the original archives present:

```sh
d=.cache/autoresearch/prior-result-rating-20261123
export PYTHONPATH=packages/scripts:.cache/autoresearch/rating-trajectory-20261118:$d
.venv/bin/python -B "$d/readback.py" verify
ruby "$d/independent_counts.rb" "$d/prior-result-rating.json"
jq -cS --slurpfile rating "$d/prior-result-rating.json" -f "$d/gate_overlap.jq" \
  .cache/autoresearch/gate-training-source-20261123/gate-training-input-evidence.json
```

All 242 related tests, lint and formatting passed. No source data request,
fitting, prediction, result rescoring or registration occurred. The three
October commitment hashes and the 70 percent criterion are unchanged.
