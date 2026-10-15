# Condition Memory Methodology Review

## Decision

Keep the sealed 24-versus-34-column comparison from PR102 unchanged. The new
history is useful input evidence, not evidence of higher prediction accuracy.
Do not interpret the sign of the condition contrast as a direct estimate of
distance, class or venue aptitude. Do not add a Yeongcheon-specific correction,
change the similarity window, or replace the existing learner in this feature
comparison. Original M0/API27 predictions and the original input reservation
remain immutable.

## Completed Pro Consultation

On 2026-10-15 the authorized in-app ChatGPT session recovered. Its model menu
displayed Pro. The completed answer displayed a processing duration of
12 minutes 38 seconds and the explicit response-completed state. Generation
was not stopped or skipped. This supersedes the access blocker, not the
historical logged-out observation recorded in PR102.

Consultation:
https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d

The submitted context described PR101/102, the fixed objective, 50 races and
534 appearances, the 1,001 admitted additional history rows, 28 withheld rows,
the 11,523 supported-history total, sparse Yeongcheon support and PDF exclusion.
The multiline input was submitted as two context messages; the remaining
question draft was not submitted and was cleared after completion. The response
nevertheless addressed the comparison and temporal-admission questions below.
No local raw data, secrets or credentials were uploaded. The advisor explicitly
limited its review to the supplied facts and public implementation, not an
independent replay of the local raw data.

## Verified Mathematical Caveat

For normalized finish z=(N-r)/(N-1), the existing form is
F(S)=(1+sum(z))/(2+len(S)). The condition contrast subtracts the smoothed form
of all recent history from the smoothed form of its similar-condition subset.
Different subset sizes therefore imply different shrinkage toward one half.

In a synthetic example with five identical finishes z=4/5 and one similar
finish, the similar form is 3/5 and the overall form is 5/7. The contrast is
-4/35, approximately -0.114286, even though all observed finishes are equal.
This is a property of the fixed formula, not a measured loss of condition
aptitude or an empirical performance result. Retain the support counts and
fallback flag; do not use the contrast sign for manual bonuses or penalties.

Older same-condition, other-venue and missing-condition counts need not form
a disjoint partition: an other-venue record may also lack condition fields.
Do not require their sum to equal older_count.

## Accepted Boundaries

A24 and B34 would be new research models sharing exactly the same admitted
training races, outcome versions, learner and common-column preprocessing.
A24 is not a rename of M0 or API27. The experiment tests the ten-column bundle,
not the causal effect of May collection or the individual value of each column.
It must not count either-arm success as portfolio success or select whichever
arm scores higher as the headline result after observing outcomes.

The 11,523 supported historical finishes are not 11,523 independent, approved
training examples. Each training target needs its own prereace covariates and
availability evidence. An old event date does not establish that the version
collected in October was available at that old target's cutoff. For the future
October block, both the earlier history event and the captured version must
precede the fixed prediction cutoff. Current cumulative API statistics must
not be backfilled into an earlier target as if they were historical snapshots.

If the October 16-18 outcomes are used for fitting or model selection, that
block is development data for those models. Preserve its independent status
only for the already sealed M0/API27 predictions. A later comparison needs an
explicit new full-population protocol and two timely single-combination
prediction commitments. No future dates or new arm are registered here.

## Proposal Not Adopted

The advisor proposed an additive three-set likelihood learner with fixed L2
regularization. That is a different learning objective from the repository's
restricted logistic baseline. It is recorded as a possible later hypothesis,
not adopted into this feature-only comparison or silently treated as an
approved recipe. No extra shrinkage transform, third arm, tuning sweep or
training approval is introduced by this review.

## Remaining Gate

The current candidate matrix remains label-free with training_approved=false
and zero fits. Further feature expansion or repeated tuning on the already
examined 27 races is not justified by the current evidence. The next material
steps are versioned official outcomes for the frozen 50-race block, paired
M0/API27 evaluation, and a separate source/availability/recipe admission review
before fitting A24/B34. Pending outcomes are not failures or zero accuracy.
The goal remains unmet; this consultation does not change its success rule.

## Verification

The synthetic arithmetic was checked independently with Python Fraction:
3/5 - 5/7 = -4/35. The three original commitment SHA256 values match PR95.
This change is documentation only; it does not edit model code, data, public
commitments or approval registries. Validation and remote checks are reported
in the associated pull request.
