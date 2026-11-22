# Recheck optional prior-result leads against the whole card

Frozen prior-source lead packet SHA256: `6c2f00d2d1690a5fe9e66b011e0ce5570404de6cae45891910c11ddb3af731ce`.

This is the read-only follow-up to the
[published nomination coverage](2026-11-23-nomination-prior-coverage.md).
Replaying the original source pins reproduced 12 positive historical
date/venue scopes and 21 scope/race/horse rows, covering 20 distinct
race/horse pairs across four preliminary fields. One pair occurs in
two scopes. October 24 Seoul still contributes three conditional
first exact-distance links. None is a confirmed starter or an approved
feature. The 34 observed preliminary keys, including the 29 without
identity-bearing details, remain in the underlying census.

The local sealed packet preserves each claim's original target race,
stable horse ID, benefit and relevant observed historical race IDs.
It references the independently published source comparison and its
archived publication receipt. No additional result or API request was
made. Results already archived as KRA HTML are not proof of an API
attempt or current entitlement.

## When a complete card exists

Run from the separate research checkout with its Python environment
and the existing whole-card evidence:

```bash
PYTHONPATH=packages/scripts:apps/api python -m autoresearch.nomination_prior_scope_recheck \
  --leads .cache/autoresearch/nomination-prior-scope-recheck-20261123/frozen-optional-prior-leads.json \
  --leads-sha256 "$LEADS_SHA256" --nomination-packet "$ORIGINAL_NOMINATION_PATH" \
  --receipt "$WHOLE_CARD_ENTRY_RECEIPT" --receipt-sha256 "$ENTRY_RECEIPT_SHA256" \
  --schedule-sha256 "$ORIGINAL_SCHEDULE_SHA256" --first-cutoff "$ORIGINAL_FIRST_CUTOFF" \
  --packet-sha256 "$PUBLISHED_WHOLE_CARD_SHA256" --pull "$WHOLE_CARD_PR"
```

Use the existing reconciled schedule, the original cutoff, and the
independently witnessed whole-card packet. An original date, cutoff
or venue cannot be replaced to make a lead pass. The check retains
all witnessed race IDs and the full declaration count. It keeps only
exact race/horse pairs with corroborated name, grade and distance as
conditional leads. A field missing from the witness is not a verified
cancellation; changed conditions, missing declarations and identity
conflicts are distinct holds.

The output is local and cannot authorize acquisition, admission,
training or scoring. First complete the existing full-card M0/API27
publication protocol. Optional collection still requires the exact
remaining historical date/venue scope, current result API entitlement,
the prior-attempt ledger and an available bounded budget. Do not
repeat or silently substitute a scope. No final card, new evaluation
window or predictive improvement was established here.
