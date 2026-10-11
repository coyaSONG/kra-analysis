# Forward Research Server Configuration

## Decision

The owner asked to choose the server configuration before requesting connection
secrets. Choose one isolated Supabase research project and one always-on Linux
collector. This is a proposed deployment configuration, not authorization to
purchase services and not evidence that any server has been provisioned.

| Component | Selected configuration | Purpose |
| --- | --- | --- |
| Research DB | Supabase Pro, Micro, separate project `kra-research-forward`, Seoul `ap-northeast-2`, initial 8 GB database disk | Frozen race membership, predictions, commit observations and result versions |
| Collector | AWS Lightsail Linux/Unix, Seoul, 2 vCPU, 4 GB RAM, 80 GB SSD, public IPv4 bundle; Ubuntu 24.04 LTS image subject to console availability | Continuous source capture and deadline-sensitive prediction submission |
| Training | Existing research machine, isolated environment and frozen data | CPU model fitting without delaying submissions; no GPU reservation yet |
| Raw artifacts | Collector disk plus private off-host object backup; content-addressed filenames and manifest hashes | Original API/PDF bytes, source receipts, models and reproducible experiment files |

Use a separate DB project rather than changing the current application's
Supabase database. This keeps research roles, restoration and experimental
schema installation away from production application data. The database size
and compute are starting allocations, not a measured capacity guarantee.
Store large PDF/model blobs outside database rows. Escalate compute only after
measured CPU, memory, disk or latency pressure, not merely the number of API rows.

Both providers list Seoul availability: [Supabase regions](https://supabase.com/docs/guides/platform/regions)
and [Lightsail regions](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html).
Record the actual provisioned PostgreSQL major version and pin the deployment
to it. Existing integration evidence is on PostgreSQL 16; a different hosted
major version must pass the same integration cases before operational use.

## Cost Envelope

Official prices checked 2026-10-11: a new Supabase Pro organization starts at
USD 25/month, including credit for one Micro project. Lightsail's public-IPv4
Linux bundle with 4 GB RAM, two vCPUs and 80 GB SSD is USD 24/month. The initial
combined baseline is therefore **USD 49/month**, before tax, usage overages,
snapshots, extra storage and other add-ons. This is not a hard spending cap.

If the existing organization is already Pro and its compute credit is consumed,
an additional Micro project starts around USD 10/month; the incremental baseline
would instead be roughly USD 34/month including the worker. Existing account
plan, credits and console checkout totals have not been inspected. Do not create
another paid organization unnecessarily. Do not enable PITR, IPv4 DB add-ons,
GPU servers or larger compute without a separately accepted need and budget.
Sources: [Supabase pricing](https://supabase.com/pricing),
[compute sizes](https://supabase.com/docs/guides/platform/compute-and-disk),
[Lightsail pricing](https://aws.amazon.com/lightsail/pricing/).

## Connections and Roles

Use PostgreSQL connections through `asyncpg`, not Supabase REST/API keys. Prefer
the direct TLS connection when the worker has verified IPv6 reachability. If
the worker is IPv4-only, use the dashboard-provided **session pooler**, port
5432. Do not invent its hostname or copy a direct-connection username into a
pooled URL. Transaction pooler port 6543 is not the selected initial deployment.
Validate the separate-transaction observation tests on the chosen connection path.
The [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
documents these alternatives and username differences.

Create two separate login roles, `kra_forward_owner` and `kra_forward_runtime`.
Neither should be a superuser or have CREATE ROLE, replication or BYPASSRLS.
The owner may create the dedicated `research_forward` schema and own its objects;
installation uses `apps/api/scripts/run_forward_b0.py install`. The runtime has
only schema USAGE, table SELECT and the existing three narrow functions
`submit`, `observe`, `observe_study`. It has no direct table writes, ownership,
administrative attributes or membership allowing SET ROLE to the owner. Merely
setting NOINHERIT is not enough to prevent role switching. Do not reuse `postgres`,
`service_role`, `anon` or `authenticated` as the collector DB identity.

Keep `research_forward` outside exposed Data API schemas. Do not grant its
privileges to Supabase API roles. Select explicit database/network access for the
worker and administration path, not open-ended grants. Follow the provider's
[custom-role controls](https://supabase.com/docs/guides/database/postgres/roles).

Store `KRA_FORWARD_OWNER_DSN` and `KRA_FORWARD_RUNTIME_DSN` in local/host secret
storage outside Git and outside chat; never print them, pass them as CLI literals
or include them in logs. Use TLS certificate and hostname verification
(`sslmode=verify-full` with the appropriate trusted CA); do not silently downgrade
to `require` or disable certificate verification. Configure and validate the
actual asyncpg client connection, not just a successful `psql` test. See
[Supabase SSL verification](https://supabase.com/docs/guides/platform/ssl-enforcement).

The existing runner needs the owner only to install and initially freeze a new
study. After that study is committed and independently observed, recurring
resume invocations can use only the runtime secret. Keep owner credentials out
of the persistent collector service. Bootstrap is a controlled, short-lived
administrative operation; do not give the worker permanent owner access.

## Worker and Backup Policy

Run a single non-root collector with one execution per study at a time, automatic
restart and bounded retries. A systemd timer/service is the proposed deployment
mechanism; none has been installed. Do not rely on a sleeping laptop, an open
chat or an unverified recurring job for deadline compliance. No public web service
or inbound database port is needed on the worker. Restrict administration to the
approved SSH/VPN path; allow required outbound HTTPS, DNS and TLS PostgreSQL.
Monitor disk, clock synchronization, process failure and oldest missing receipt.

Freeze the complete official race universe and obtain commit observation before
the earliest T30 deadline. An internal earlier submission target must leave
time for retries; it does not change the contractual cutoff. Late or missing
submissions stay visible in the full universe. Separate large backfills, PDF
research and model training from deadline-sensitive scheduling and API quotas.
Pin one deployed code/model version per frozen study; no automatic pull/restart
may change an active study's implementation digest.

Supabase Pro supplies daily DB backups with seven-day retention. Those backups
do not include Storage object bytes, and restored custom-role passwords require
re-establishment. Back up original capture bytes separately, export the ledger
after capture runs, and test restoration into an isolated environment. Never
restore over the live ledger as an ordinary retry. Provider backup is recovery,
not an independent pre-race timestamp or protection from a malicious DB owner.
Source: [Supabase backup scope](https://supabase.com/docs/guides/platform/backups).

## Deployment Acceptance

Before operational use, verify account/budget approval, actual endpoints, TLS,
PostgreSQL version, role membership, lack of runtime write privileges and
separate connections' commit observations. Run the PostgreSQL integration suite
in a disposable schema with dedicated test roles, never destructive tests in
the production research schema. Exercise bootstrap, runtime-only resume,
unchanged retry, conflicting payload rejection, deadline rejection and full
membership accounting. Confirm an actual persistent worker is running and that
backup restore works. Only then register a real future study with published cards.

The existing SQL admits **B0 only**. Trained M0/M1 challengers need an explicit
arm contract before submission and must not masquerade as B0. Multiple-arm
success cannot substitute for one exact three-horse prediction per race.

## Current Status

On 2026-10-12 KST the owner explicitly deferred paid servers and directed local
research to continue. Do not provision or purchase this proposed configuration
without a later authorization. No owner/runtime credentials are needed for the
current local official-history reconciliation work.

Configuration selected; paid resources, roles, credentials, network rules,
worker scheduler and backups have **not** been created. This decision answers
the owner's server question; it does not unblock operational forward submission
until the deployment acceptance checks pass. Restricted local cohort/model work
can continue independently. The 70% target remains unchanged and unverified.
