# B0 forward registration path

## Purpose and Trust Boundary

`apps/api/scripts/run_forward_b0.py` connects official schedule capture, complete universe freezing, API26 raw replay and a fixed untrained B0 rule to PostgreSQL. B0 selects the stable horse IDs at the three smallest numeric gates. This is an operational baseline, not the existing strongest model and not a 70% claim. Research history is not an input. Missing predictions remain in the full population report.

The ledger trusts the collector process, schema owner and DB clock. It records exactly what was submitted and when a separate transaction observed that committed submission. It is **not external notarization** and does not protect against a malicious DB owner. Runtime credentials must belong to a separate, non-owner, non-superuser role with no inherited table-write privileges. The script checks direct write privileges before using runtime connections. It does not create credentials or silently deploy into the application's production migration chain.

## Installation and Execution

The database administrator must supply two separately scoped PostgreSQL connection configurations as environment variables, `KRA_FORWARD_OWNER_DSN` and `KRA_FORWARD_RUNTIME_DSN`. Do not put their values on command lines, in reports, or in Git. The runtime role must already exist; installation grants only research-schema usage, SELECT and three narrow function calls. Installation must be performed with the intended schema owner. An existing schema is not overwritten.

From the repository root with API dependencies installed:

```bash
PYTHONPATH=apps/api:packages/scripts python apps/api/scripts/run_forward_b0.py install --runtime-role <existing_restricted_role>
PYTHONPATH=apps/api:packages/scripts python apps/api/scripts/run_forward_b0.py run --study b0_20261016 --race-date 20261016 --archive .cache/autoresearch/forward-b0 --api-key-file <secret-file>
```

The default schema is `research_forward`; `--schema` can select an explicitly isolated test/deployment schema. The run command is also the resume command. It reads an existing study and original submissions first. Before first submission it writes exact canonical request bytes locally; a pending request is revalidated against its retained raw source before retry. Once DB receipt exists, retries recover those original bytes and first observation. They never recompute an already-submitted prediction from a newer roster.

Every run retains a timestamped report. `awaiting_card` means the requested day is not fully reconciled across dated national and regional sources; `awaiting_database_configuration` means cards exist but separate DB settings are absent. Neither means a completed future test. A changed source/code contract under an existing study is not silently accepted. The fixed code hash includes the service, SQL, runner and entry validation code. A failed or short roster leaves `missing_submission`; there is no invented fallback combination. Run history collection separately so it cannot delay this baseline.

## Database Guarantees

The owner freezes canonical universe bytes and all memberships in one explicit transaction before any deadline. A second connection records observation of its commit before predictions are admitted. The schema permits only one study per race date and synthetic flag, preventing runtime study aliases from multiplying attempts. Runtime cannot create or change studies.

The submission function locks a membership row before reading `clock_timestamp()`. It accepts one fixed arm and one payload for that race. Same bytes return the original receipt even after deadline; different bytes conflict. The DB recomputes the payload digest and fixed B0 selection, verifies membership, source timestamp and implementation/universe binding. Direct table writes are denied to runtime, and update/delete triggers also reject accidental owner edits. Schema destruction/admin override remains within the explicit owner trust boundary.

The service commits, closes that connection, and then observes through a new Read Committed transaction. SQL compares `pg_current_xact_id()` with the writer ID to reject self-observation, including savepoints. Observation time after cutoff is `commit_timeliness_unproven`, not proof the actual commit was late and not a backdated success. A successful insert or transaction-start timestamp alone cannot certify timeliness. These boundaries follow the [PostgreSQL clock semantics](https://www.postgresql.org/docs/16/functions-datetime.html), [transaction information functions](https://www.postgresql.org/docs/16/functions-info.html), and [fixed SECURITY DEFINER search-path guidance](https://www.postgresql.org/docs/16/sql-createfunction.html).

## Evidence and Remaining Work

Actual next-card check at 2026-10-11T11:39:39Z returned `awaiting_card` for 20261016. Original schedule bundle is `.cache/autoresearch/forward-b0/b0_20261016/schedules/20261011T113939.107558Z_f7a37192e181/capture.json`; report is `.cache/autoresearch/forward-b0/run_20261011T113939579674.json`. Owner/runtime forward DSN environment variables are both absent. No operational schema installation or real future submission has occurred.

Local pure tests: 12 passed; full API type checking: 179 source files passed. First CI run `38136476926` executed all 16 new PostgreSQL integration cases without skipping, within 50 passing API integration tests. The unit suite had 339 passing tests and two existing skips. Test fixtures create and remove only random test schemas/roles. Synthetic HTTP captures exercise the complete run/resume path but are not actual KRA predictions. Final refinement CI results are recorded in the PR before merge.

Actual source pins: schedule manifest SHA-256 `1b7a22be71b2f98f27db84d721b52f96b63ac7c5f00ec011fb9dbe116a7ea28c`; run report SHA-256 `fc388dec5a589626c1f8d9a4cb4ad1e6663a1e4c59895598b19fd237be78398c`. Both are local post-capture evidence only. Gitleaks passed; the first dependency audit failure exactly matched the previous 17 known package/version/advisory records.

Still required for the research goal: explicitly provision the production research owner/runtime connections, run this same command when genuine future cards exist, retain full-population receipts and outcomes, and evaluate the unchanged exact-three target on that full frozen universe. This increment adds no trained challenger and claims no improvement in model accuracy.
