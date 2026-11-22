# November 8 external form generation and identity evidence

This is a source registry note for the unchanged November 6-8 historical
panel, not a pre-race prediction, registration, source approval or score.
The original common cutoff is 2026-11-06 01:15 UTC (10:15 KST).

## Exact object observation

The [exact Singapore Pools form generation](https://storage.googleapis.com/sppl-forms/main/eng/KOR_FORM_081126.pdf?generation=1793864281477594)
has Cloud Storage creation time 2026-11-05 07:38:01.483 UTC, 17 hours
36 minutes 58.517 seconds before the original cutoff. Cloud Storage
[documents creation time and generation as non-editable version metadata](https://docs.cloud.google.com/storage/docs/metadata#non-editable).
This establishes a bound on the existence of these external bytes in
storage, not public access or research availability at that time, or
publication of the original KRA API26 bytes.

One anonymous metadata GET and one exact-generation media GET returned
HTTP 200 on November 22, at 14:02:20.602746 and 14:02:56.357369 UTC.
The 4,504,262-byte PDF matched the generation's size and MD5; its
SHA256 is `2e74dd3793fb3909b29bfd37e4c12b1fc6846e646f64fac2bd2f00167262f92e`.
Metadata SHA256 is `81a7543ab21a39b63358d54ef7099b0353cfe7df3d45772e09340e7c145ccff6`.
The first 4 MiB cap withheld the media request. The exact later transfer
was bounded to the stated size, lower than the already verified 4,611,017
bytes of the equivalent November 15 form. The reserve and receipt for
both reads are preserved. No retry, alternate version, credentials,
outcome fetch or KRA data API was used.

## Exact scope and unresolved fields

Join by physical venue, date and scheduled start with the Singapore
clock converted to KST, then verify printed distance and class number
or OPEN. All 17 mapped fields and their 161 declarations match on
gate and normalized literal English horse name. Age, sex and assigned
weight also match for all 161. The stable horse ID comes from the
unchanged local API record, not the external form. It does not prove
actual starter status or full KRA literal grade semantics.

| Physical venue | Races | Matched declarations |
| --- | ---: | ---: |
| Seoul | 11 | 108 |
| Yeongcheon | 6 | 53 |

In particular, external R9 is original `20261108_4_3`, the 2000 m
grade-2 race with ten declarations. Do not match race numbers across
publishers. Independent reading of each top table agreed on all 17
venues and runner gate lists. The other 34 races of the original
51-race, 496-declaration panel remain in the ledger, outside this PDF.

The career tuple differs for 50 matched runners, 27 at Seoul and 23
at Yeongcheon. Each of the 50 has a higher local API starts figure;
29 differ only by one additional local start. Eleven Seoul runner
jockey names differ as strings. The cause, period and exact inclusion
rules are unverified; do not fill or replace API columns. The 710
recognized past-start dates in the PDF precede the creation day in
Korea; this does not authorize all fields as historically available.

The local `singapore-nov08-yeongcheon-20261122/external-form-evidence.json`
records the original keys, exact source pins and observed differences.
Its SHA256 is `7f8cbc17531111554ec53dc34514bdbbe1b0b86ebb3858a60c7bfa3aec889743`.
193 related offline tests passed, including the version, deadline,
transport-state and actual byte/roster replay. Original predictions,
result policy, approved models and the 70% goal remain unchanged.
