# Historical sectional endpoint arithmetic

## Result and interpretation

The original May 1-14 archive retains **102 races and 1,029 observations**.
Across Seoul and Busan, **3,262 named endpoint checks** produce 2,805 exact
equalities, 417 structurally unsupported spans and 40 missing-value checks.
There are no remaining evaluable arithmetic conflicts. Jeju's 298 rows
remain in the report but have no independent cumulative counterpart for
this test. They are not silently removed or assigned successful checks.

The new finding is semantic: **Busan's 1300m `8-6F` column measures the
initial 100m, not a 400m section**. A first literal-name pass retained 44
positive values with endpoints outside the race. The original results page
links to the [official sectional explanation](https://race.kra.co.kr/raceScore/cornerRecordDesc.do),
whose distance table and accompanying explanation explicitly identify the
1300m exception. After applying that documented 0-100m definition, all 44
values equal the cumulative 100m checkpoint. This is not a fitted tolerance
or a change made to improve model accuracy.

The same official guide distinguishes overlapping final sections and
distance-dependent initial spans. The implementation checks each span
separately and never sums S1F, final 600m, final 400m and final 200m as if
they were a nonoverlapping partition. Guide entries for other distances do
not authorize unseen result-table layouts.

These results improve measurement understanding, **not measured prediction
performance**. No target outcomes from the October 50-race development
block, saved-model scoring or fitting were used. The 70% exact-single-triple
goal remains unmet.

## Full-population denominators

| Scope | Original observations | Named checks | Exact | Unsupported span | Missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seoul | 431 | 862 | 834 | 0 | 28 |
| Busan | 300 | 2,400 | 1,971 | 417 | 12 |
| Jeju | 298 | 0 | 0 | 0 | 0 |
| Total | 1,029 | 3,262 | 2,805 | 417 | 40 |

The denominator is comparisons, not independent training samples.
Each Seoul final-600m and final-200m relation has 417 exact and 14 missing
checks. Each Busan initial-200m and final-600m relation has 298 exact and
two missing checks. Other Busan relations use the labelled metre positions
in the distance-specific cumulative header, including cases where the S1F
position supplies a differently named segment's endpoint.

An unsupported span has an out-of-race endpoint and a blank printed
segment. It does not establish the cause of an arbitrary API zero.
A nonblank value in such a span is separately flagged rather than dropped.
Zero duration is not accepted as a valid elapsed section; absent operands,
nonincreasing clocks and unequal arithmetic have distinct statuses.

## Eligibility is separate

The existing support policy is unchanged: **1,001 supported observations,
11 observations withheld for a whole-race rank/source conflict, and 17
other unsupported starts**.

The 11-row conflict race contributes 20 exact checks and two missing checks.
Thus passing arithmetic does not resolve its rank discrepancy or restore
training eligibility. The other 17 unsupported observations contribute
38 missing and four structurally unsupported checks; Jeju's unsupported
rows still have no independent checks. All records remain visible with
their history eligibility and arithmetic scope.

Among already supported observations there are 2,785 exact checks and
413 unsupported spans. This is still not a feature-ready training-row
count: source timing, reference-group membership, future roster coverage
and a separately approved feature definition remain separate questions.

## Source register

Historical source root:
`.cache/autoresearch/observed-history-extension-20260501-14`.
Seed SHA256:
`561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407`.
Official archive SHA256:
`8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd`.
The existing API/HTML identity and cell-mapping audit is replayed before
arithmetic; unresolved cell conflicts stop this derivation.
The report retains all 102 original official receipt/raw pins and URLs,
plus the original acquisition status counts, including 44
`empty_unconfirmed` units. No blank response becomes a no-race declaration.

The official guide was captured once, without retries, at
**2026-10-20T17:51:17.717455Z to 17:51:17.911965Z**, HTTP 200,
6,397 bytes, EUC-KR. Local evidence directory:
`.cache/autoresearch/sectional-arithmetic/guide-20261020T175117Z`.
Raw SHA256:
`4ad717274decab45d501f1a8884935544117beeb65c866ee000063e884a80ab7`.
Receipt SHA256:
`4fc08a08e789ebfe94b2adea99bd9fc6d15c925614472fe72c67849488711549`.
The replayer verifies both pins and the guide's explicit 1300m distance row.

This newly collected guide establishes a **current documented definition**,
not its publication date in May or before the original October cutoff.
The historical observations were collected on October 15; they cannot
become May pre-race training examples. No newly interpreted feature is
retroactively inserted into the frozen A24/B34 inputs.

## Verification and reproduction

The saved [report](experiments/2026-10-20-sectional-arithmetic/report.json)
has SHA256
`94fbd92c4f5506da4516bfe1e92858018ca9b2be24f567013eb8a4cccd53f18d`.
It records the implementation and source-mapper hashes, all observations,
venue/distance totals, relation totals, eligibility counts and exceptions.

From the isolated checkout:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B \
      -m autoresearch.sectional_arithmetic_audit

This prints a fresh timestamped report; it does not write or make network
calls. Preserve the published report rather than overwriting it.

A separate local `HTMLParser`/`Fraction` implementation, importing neither
the new auditor nor its arithmetic functions, read the 102 original pinned
HTML files. It independently checked 731 Seoul/Busan observations and
reproduced every row's check counts and the totals above. Its local
companion is `.cache/autoresearch/sectional-arithmetic/independent_check.py`.
This is independent computational verification of the same source bytes,
not independent truth or external model validation.

The regression suite covers exact decimal differences, missing/zero
distinctions, the 1300m special case, each observed Busan layout,
unsupported positive spans, wrong headers, missing identities/gates,
changed hashes, printed duration conflicts and positive-time excluded
starts. CI runs these checks with the existing historical audit tests.
Local validation passed 194 related tests, including 37 new cases, plus
Ruff lint/format checks. Required CI and normal-merge receipts are on the PR.

## Next decision

The endpoint arithmetic stage of the
[no-fit proposal](2026-10-20-exact-set-research-priority.md) is complete
within the observed source scope. It does not establish whether time
gaps or speed allocation add transferable information beyond ranks.
Next, retain these eligibility and endpoint boundaries while inspecting
descriptive time variation, within-historical-race reference support and
same-horse repeat coverage, without October target access or fitting.
Jeju's temporal semantics need a separate documented interpretation before
inventing cumulative relationships.

No model, prediction, prior reservation, population, training budget or
future registration changed. Dates and N remain unset. No automatic model
promotion or 70% success claim follows from this audit.
