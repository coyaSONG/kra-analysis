# Prospective publication slot binding

New live admissions require `condition-forward-protocol-v2`. This is code
preparation, not a registered study or an approved evaluation interval. The
actual review registry stays empty; models, fit receipts and M0/API27
commitments are unchanged. No real prediction or publication slot is created.

## Accepted publication identity

The v2 protocol adds `publication_slot` with exactly three keys:
`repository`, `pull_number`, `document`. Repository must be `coyaSONG/kra-analysis`;
the number must be a positive integer, not a bool or numeric string; the document
must be `docs/research/commitments/condition-forward-v1/{study_id}/paired.json`.
The paired payload/path keep their existing version because their numerical
meaning is unchanged. Protocol v2's hash binds the new slot into the prediction.

The separately reviewed registry record adds `prediction_publication_pr`,
equal to the protocol slot's number. It cannot equal the protocol-publication
PR or another reviewed study's prediction PR. Historical v2 archive replay also
requires it to differ from the selected separate approval PR. No fallback or
alternate slot field is allowed. The original v1 contract is not rewritten;
it remains supported by the historical reader, not the new live admission gate.

For an actual future study, the intended prediction PR must be identified
and bound before protocol publication and approval. An existing open draft PR
can serve as the named future slot; no prediction bytes need exist at that
time. Creating that PR is not a prediction, approval or timely publication.
No real draft PR or placeholder protocol is created by this implementation.
After inference, only the exact canonical paired bytes may be merged in that
bound PR before the original earliest block cutoff. Do not close it and switch
to another PR to repair a missed deadline. A later study needs its own separately
reviewed protocol and must not reuse this slot or reset the original population.

`stage` reports the exact slot along with the staged hash. `witness --pull`
still takes an explicit number, but now rejects another number before numerical
replay, publication capture or creation of a witness directory. It checks again
after local replay before capture. Successful witness reports include the slot.
The existing publication verifier still checks repository, original merge-tree
document and byte hash; a matching PR number alone is not publication evidence.

## Historical attribution

The historical reader handles v1 and v2 from their original archived bytes.
For v1, declared-slot and matching-slot facts are null, not retroactively true.
For v2, it validates the original declaration, original review binding and
selected archive PR/path. The report records the slot-validator module hash
with the other verifier hashes. It does not invoke the live admission gate,
current runtime, model scoring, fitting or network collection.

`selected_archive_matches_declared_slot` means the selected archive reference
has the declared identity. It is not proof the referenced files exist: loss of
the original prediction witness remains `pending_evidence`, with submission
closure unverified and scoring disabled. A structurally different chosen PR
raises a conflict; it is not turned into a race miss. Correct v2 publication
attribution still does not establish full input provenance or population.

## Remaining gates

This binds one accepted slot but does **not** independently prove that it
existed before cutoff, that it was never timely merged, or that no required
weekly submission was omitted. No new absent/late/invalid scoring state is
created. A source-backed closure collector and replay policy must establish
post-cutoff status of every prebound obligation using preserved authoritative
responses, including missing weeks and corrections. Missing local files cannot
supply that evidence.

Unique PR numbers are not proof of unique physical race enrollment across
aliases, renamed studies or clones. Umbrella/weekly authority linkage, full
population closure and target admission remain necessary. The v2 identity
boundary narrows accepted submissions; it is not completion of the prospective
evaluator, a scientific improvement, or evidence toward the 70% accuracy target.

## Validation

A new regression failed against the previous code because an unbound PR reached
numerical replay. Updated tests cover malformed/missing slots, wrong repository
or path, bool/string IDs, mismatched review, reused PRs, correct staging/witness,
historical v1 compatibility, v2 attribution, missing evidence and live-version
drift. All studies and PRs in these tests are fictional temporary fixtures.
The snapshot fixture now binds PR 902, matching its existing separate protocol
900 / approval 901 / prediction 902 archives; the original inconsistent fixture
was rejected rather than relaxing the production check.

Final validation: **432 passed in 41.73 seconds** across forward publication,
historical publication, original snapshot replay, population chain and ledger,
semantic review, outcome accounting, versioned results and local M0 evaluation.
Ruff lint/format and whitespace checks passed. Both stored models, the fit
receipt, M0/API27 public commitments and the empty actual review registry retain
their pinned SHA256 values. No real fit, inference, registration or collection
was performed for this implementation.
