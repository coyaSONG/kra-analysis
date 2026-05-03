# `enriched_data` pipeline is intentionally on hold

`basic_data` is the active storage layer in production. `enriched_data` columns exist in the schema but are NULL by design until an offline A/B verification confirms the feature lift over `basic_data`-only models. The full canonical-v2 three-layer architecture remains deferred until that gate passes.

Implications: do not backfill `enriched_data`; do not treat NULL there as a bug; do not block other work on enrichment activation.

Related: `docs/knowledge/decision-2026-03-15-skip-pipeline-overhaul.md` (broader pipeline freeze, of which this is the narrow data-layer slice). Promoted from `docs/knowledge/decision-2026-05-03-enriched-data-intentional-hold.md`.
