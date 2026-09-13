# Server deployment and rollback

## Current deployment hold (2026-09-13)

Do not execute the historical cutover steps below without the audit gates.
Production app/DB run, but both delivery worker containers are absent. The
channel backlog is 2519 sends plus 5 removals. The local candidate is not deployed.
Read `../TECHNICAL_AUDIT_2026-09-13.md` and `../PROJECT_CONTEXT.md` first.

Required before rollout:

1. Restore-test the local dump in isolated PostgreSQL 16, not production.
2. Reconcile the production schema (including historical `retired` records) with
   migration baseline. Apply candidate migrations only to the isolated DB first.
3. Test retry, restart, overlapping filters, blocked users, and uncertain sends.
   The current local worker still holds a transaction across HTTP: do not claim exactly-once.
4. Obtain explicit approval for backlog policy, admin test messages and cutover.
5. Keep `DELIVERY_ENABLED=false` during deployment. An approved timezone-aware
   `DELIVERY_NOT_BEFORE` is required before enabling it. Older tasks remain held,
   not deleted or mislabeled sent. This is a cutover guard, not a freshness proof.
6. Never run the whole shared stack, alter Traefik, or touch another bot's volumes.
7. Check worker presence, heartbeat/queue progress, failed/dead_letter tasks and
   actual message IDs. `/healthz` alone checks only app/database availability.

The local snapshot `backups/audit-20260913T0210/database.dump` has a verified
catalog, **not a verified restore**. All snapshot bytes were streamed to the PC;
no permanent backup file was created on the server. Its folder is owner-only.

## Historical initial cutover (not an operational runbook)

## Before changing production

1. Keep the existing GitHub workflow in legacy mode until `CENTRAL_INGEST_URL` and `CENTRAL_INGEST_SHARED_SECRET` are configured.
2. Copy the current `state/last_seen.json` and an export of every locally readable approved user ID into a dated backup. Do not attempt to read GitHub Secrets; they are intentionally non-retrievable.
3. On the server, create `server/.env` from `.env.example`, with new random secrets. Keep it outside Git and set permissions to owner-only.
4. Start `docker compose -f server/docker-compose.yml up -d --build`, then check `GET /healthz` through the reverse proxy.
5. Configure Telegram webhook with the random secret header, then test one administrator approval and one delivery in a non-production chat.
6. Create a local, access-restricted one-ID-per-line export from the current approved-user list and run `LEGACY_USER_IDS_FILE=/secure/path/users.txt python -m server.import_legacy_users`. It records every import in the audit trail. Compare its count to the snapshot before enabling the GitHub server endpoint. Do not place the export in Git.

## Cutover

Set GitHub Secrets `CENTRAL_INGEST_URL` and `CENTRAL_INGEST_SHARED_SECRET`; then set the collector Repository Variables to the validated all-category scan limits (for example `MAX_LISTINGS_PER_RUN=100`, `LIST_PAGES_PER_RUN=3`, `MAX_DETAIL_FETCHES_PER_RUN=100`). Run one workflow manually and verify: received rows, queued outbox tasks, one controlled delivery, and no duplicate row for a repeat request. Only then leave the schedule enabled. The legacy direct-Telegram branch is bypassed when the URL exists.

## Rollback

Do not remove `CENTRAL_INGEST_URL`: that used to enable a second, uncoordinated
transport. The local candidate now fails closed unless legacy transport is
explicitly opted into. Stop only this project's workers, roll back this project's
code release, keep delivery paused, and verify DB compatibility. Never automatically
restore an old database over new users/audit/payment records. Whole-DB restore is
a separately approved disaster-recovery operation. Retain PostgreSQL and all tasks.

## Backups and recovery test

Run `pg_dump -Fc "$DATABASE_URL" > rent-$(date -u +%Y%m%dT%H%M%SZ).dump`, checksum it, and periodically restore into a separate empty database with `pg_restore --clean --if-exists`. Verify row counts in `users`, `payments`, `listings`, `deliveries`, and `outbox_tasks`. PostgreSQL data and payment/audit records are never hard-deleted.
