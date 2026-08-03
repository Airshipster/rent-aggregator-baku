# Server deployment and rollback

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

Remove `CENTRAL_INGEST_URL` from GitHub Secrets (or set it empty); the workflow immediately resumes its previous direct path. Restore `state/last_seen.json` from the dated backup and reset the repository only to the recorded `git-head.txt` if the code rollback is required. Do not delete PostgreSQL: stop the server stack and retain its volume and immutable payment/audit records for investigation.

## Backups and recovery test

Run `pg_dump -Fc "$DATABASE_URL" > rent-$(date -u +%Y%m%dT%H%M%SZ).dump`, checksum it, and periodically restore into a separate empty database with `pg_restore --clean --if-exists`. Verify row counts in `users`, `payments`, `listings`, `deliveries`, and `outbox_tasks`. PostgreSQL data and payment/audit records are never hard-deleted.
