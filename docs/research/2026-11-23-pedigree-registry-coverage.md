# Pedigree keys: archive coverage and acquisition limits

This is a source audit, not a retrospective feature fill. It keeps every
original declaration in the October 16-18 card (50 races, 534 declarations)
and November 20-22 card (51 races, 540 declarations). Their original first
cutoffs remain `2026-10-16T01:20:00Z` and `2026-11-20T01:15:00Z`.
October used the original publicly witnessed panels. November used the
retained pre-cutoff local panels, which do not constitute a timely public
prediction. Neither scope was changed or opened for a new evaluation.

## Official source boundary

One anonymous GET of the [Horsepia Jeju detail form](https://www.horsepia.com/hp/pa/hh/PAHH2053/index.do)
returned HTTP 200 at `2026-11-22T20:52:15.816243Z`. No redirect or retry.
The form lists separate horse and parent registry numbers. Its search
posts filters such as birth date, while its column choices are applied
to the result grid in the browser. The observed request does not
establish a way to ask for only child and parent identity fields.
No search, export, authenticated API call, or registry rows were
obtained. The pre-search empty grid is not a zero-row result. Horsepia
registry numbers cannot be treated as API8 horse numbers without an
independently verified mapping.

The [API47 pedigree catalog](https://www.data.go.kr/data/15173126/openapi.do)
describes sire and dam names, not stable numbers for those parents. The
[Jeju nomination API catalog](https://www.data.go.kr/data/15133774/openapi.do)
does not list parent fields. These two catalogs were read as documentation
only. The form and catalogs do not establish API access, quota, or
data availability for the requested identities.

## Exact archive overlap

`full_year_2025.json` (59,465,360 bytes) matches blob
`0fe3b832ce602b925d645ac8ac74def83da38be5` in the
[PR #95](https://github.com/coyaSONG/kra-analysis/pull/95) merge tree.
The retained server record dates the merge to `2026-10-14T06:33:13Z`.
That proves repository possession of these bytes by that time, not the
provider's acquisition or publication time for the individual records.
All 1,758 legacy races lack a `snapshot_meta` key. The original
[training rejection](2026-10-11-production-training-evidence.md) stays
in force. Only child and parent identity fields were projected from the
legacy file; no results or cumulative performance fields were used.

A candidate requires the original race, gate and child identity; the
legacy nested profile must agree with its child roster ID and name. Each
parent needs a nonconflicting positive number observed together with
the corresponding printed name. This counts declarations with **both**
candidate roles, not distinct horses, accepted features, or forecast hits.

| Venue | Oct 16-18 | Nov 20-22 |
| --- | ---: | ---: |
| Seoul | 126 / 229 | 142 / 235 |
| Jeju | 0 / 137 | 0 / 130 |
| Busan | 39 / 102 | 53 / 109 |
| Yeongcheon | 58 / 66 | 53 / 66 |
| Whole original card | 223 / 534 | 248 / 540 |

In all 267 Jeju declarations, the child ID was absent from this legacy
roster. This does not mean those horses have no pedigree. October had
310 child IDs absent at the declaration grain and one unmatched printed
panel at both roles. November had 287 absent and four unmatched printed
roles per parent; one additional sire conflicted with the printed name
while the dam could be linked. The three earlier Seoul API8 receipts
were replayed, but all six of their parent roles lack a legacy candidate
to compare. No legacy candidate was independently confirmed by those
controls, and no new native ancestry identity was verified.

## Research decision

Of 225 November declarations without a known comparable own start,
82 had a printed same-sire link to at least one earlier horse with a
finish confirmed by both retained result sources. The legacy keys give
equal candidate sire numbers for at least one such peer in only 15 of
the 82. Only 1 of the 17 declarations with two distinct peers spanning
two earlier dates retained that support after the candidate-number
check. These are source-reach counts, not evidence of predictive gain.

Do not substitute this archive for missing pedigree inputs or infer a
parent identity from a name. To test pedigree, first obtain a scoped
identity source with a retained availability clock, an exact crosswalk
and verified coverage including Jeju. Any later comparison with own
prior form or a pedigree fallback still requires a separate prospectively
registered whole card. For now, preserve new whole cards and their
timely inputs ahead of pedigree-specific requests. No outcome set,
forecast, model, performance metric, or training admission changed.

| Preserved evidence | SHA256 |
| --- | --- |
| Legacy repository bytes | `60b0a91aa5bc9d864ea84904f560a4afef62e2ee59db07171b300c964105d160` |
| Horsepia form body, 202,201 bytes | `ab0641a4742c91b1f32b6624613c6e7d53a425dd32ce9e9bbd568aecb77ed34e` |
| Form receipt | `ba99ab54b28f9847c22391bacdef926c0815fbfd59fa1a51976710e524b02c05` |
| Form request reservation | `0bbe26f307cc6613826044b4068876b3bbd0acf05c763d9f060735892ca6da61` |
| Original panel audit | `dfeecdd2a30b0ea2f95e0864b84acd70f48e4e41698eebc15ad068f84923dea4` |
| Earlier rank-peer reach audit | `9f635f49c61040fda942b84cd7e088fd906c452197c9aea9aa3ebefb38bb3f09` |
| Sealed ancestry overlap and missingness audit | `73fe2c02f570d81e23a6960ecd67a5cf1af729d34b5a50db8bb417598465609b` |

The private `jeju-bulk-pedigree-20261123/` archive preserves the raw form
and receipts and pins the earlier evidence. `pedigree_overlap.py verify`
replays the comparison without calling either provider. A separate Ruby
readback reproduced the eight venue counts; 253 focused local tests
passed.
