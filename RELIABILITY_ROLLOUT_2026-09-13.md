# Reliability rollout: prepared, not deployed

## Current blockers

- The server's ordinary Bina source request returns HTTP 403. Successful GitHub
  runs do not prove server access. No access-control bypass/proxy rotation added.
- Local restore blocked by Windows Smart App Control (official PostgreSQL 16.15
  ZIP from https://www.enterprisedb.com/download-postgresql-binaries ). Protection
  was not disabled. Owner was asked about an isolated temporary server restore.
- SQL integration/restore test is mandatory before deploying these migrations.
- Primary collection every 120 seconds is a configured target, not a measured
  source-publication SLA. Source updatedAt/photo timestamps are not creation time.

## Snapshot and rollback

Fresh download-only snapshot is in backups/pre-reliability-20260913. The manifest
contains SHA256 and size. Data never left the owner's PC after download. The
script no longer streams dumps back to production for catalog checks.

Before switching, verify a complete isolated restore, counts of users/payments/
listings/deliveries, both migrations and retention idempotency. Export all affected
pending task IDs/statuses into a local rollback file. Do not delete journals.

Rollback order:
1. Stop ONLY this bot's host watchdog timer and collector/delivery containers.
2. Leave Telegram commands paused or on a compatible release; do not start legacy
   delivery code against new cancelled/uncertain statuses.
3. Revert the bot's current release link to the captured previous release and
   retain DELIVERY_ENABLED=false. Never use compose down -v.
4. Prefer forward repair: additive tables preserve originals. If full database
   restoration is necessary, first capture new users/payments/updates since the
   snapshot; restore to a NEW database and reconcile before switching. Never
   overwrite live payment/access history with an old dump.
5. Re-enable delivery only after confirming no uncertain task will be resent and
   after a fresh cutoff/recipient scope is explicitly chosen.

No rollback operation has been run.

Read-only retention preview on the live database found 1,874 channel send tasks
and 14 private send tasks older than seven days (task creation or listing first
observation). These counts are previews, not completed cancellations.

## Candidate components

- server/collector_service.py: separate process, fixed 120-second target, durable
  discovery queue and payload spool, session advisory singleton lock. Spool intake
  uses stable idempotency keys. Details submitted individually to reduce delay.
- server/delivery_queue.py: claim/commit before network, per-attempt audit, no DB
  transaction across Telegram call, terminal 403, shared bot 429 cooldown.
  Lost send responses and abandoned send claims become uncertain. This avoids
  blind duplicates but requires operational reconciliation; not exactly-once API.
- server/retention.py: cancelled send tasks older than seven days; original rows
  and uniqueness preserved. Removal notices are not classified as old listings.
- Private worker defaults admin_only; channel monthly/Baku/apartments only.
- server/db.py: migration checksum ledger. Existing unversioned deployments must
  be explicitly baselined after schema verification, not re-run historical data
  migrations. Command: python -m server.db --baseline-legacy; then migrate.
- Host watchdog: fixed container allowlist, no access to other bot processes in
  its logic, no Docker socket inside collector/worker. Shared Traefik untouched.
- GitHub standby is activated only by COLLECTOR_ROLE=standby AFTER server health
  endpoint is deployed. Authenticated readiness is recorded and read by primary.
  A fresh source_blocked state prevents switching IPs to bypass source denial.

## Limits still requiring work/verification

This is NOT a completed HA platform. Standby depends on the central intake/DB;
whole-server failure prevents delivery. GitHub schedule remains best-effort and
cannot guarantee a 5-minute takeover. An independent execution/DB failure domain
and external alert transport must be selected for a paid SLA.

Remaining before production: permitted source access, full PostgreSQL tests,
restore/rollback drill, migration baseline verification, channel/private E2E
(admin only), bounded release switch, latest collector removal checks, persistent
alerts and uncertain-task reconciliation UI, long-running backlog coverage tests,
seven-day latency observation, independent editable filter drafts. No claim that
all architectural/product defects are fixed.

Thirty-three unit tests pass as of this update. No Telegram messages were sent,
no old tasks cancelled on production, no server configuration changed or GitHub
commit pushed. Three exact-repository unread failure emails marked read; other
repository emails were not opened or modified.
