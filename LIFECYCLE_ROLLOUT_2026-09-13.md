# Lifecycle, admin monitoring and collection cadence

## Deployed and checked

Current: /opt/Telegram-bots/bots/rent-aggregator-baku/releases/20260913-lifecycle-r4.
All four application services use rent-aggregator-baku:20260913-lifecycle-r4.
PostgreSQL, Traefik and SciTopus were not restarted or reconfigured.
Migration 014 adds message_cleanup_receipts; earlier migration hashes preserved.

Channel cleanup deletes posts younger than 48 hours; older posts become a compact
unavailable marker without preview/keyboard. Private cleanup edits the existing
rich message, retaining content and adding the marker. HTTP 429 is deferred;
timeouts of these idempotent edits can retry. Missing/already edited messages
are accepted as completed. A test rich message was sent only to the admin;
Telegram returned the same message ID with the marker after edit.

Retain cleanup journal for 14 days AFTER confirmed cleanup with the new receipt.
Then remove task/attempt details and message references; retain minimal delivery
identity rows and root IDs for deduplication. Unresolved cleanup is not discarded.
132 old closed listing payloads with no remaining message references compacted.
286 legacy channel-removal tasks requeued for compact cleanup; they are not all
claimed completed. Hourly compaction runs in the channel worker. Source status
is confirmed by API, never inferred from an HTTP access failure.

Status checks use one GraphQL request for up to 50 delivered listings per cycle.
All responses validated before applying any status; incomplete/failed batch does
not remove listings. New candidates are prioritized over existing records.
Detail work has a 90-second cycle budget; unprocessed candidates remain in PG.
Nominal discovery interval is 120 seconds, not a guaranteed publication SLA.
Delivery workers prioritize new sends over cleanup backlog.

Admin-only System status is present in main menu and settings, RU/AZ/EN. It shows
heartbeat, last success, expected cadence, queues, held tasks, internal delivery
latency and incident codes. Alerts report changed incident sets/recovery rather
than repeating the same incident every six hours. Retried failed alert sends
have a 15-minute delay. Commands inspect only local PostgreSQL, not Bina live.
The reference was read-only /app/src/system-status.ts in scitopus-app-1.

GitHub COLLECTOR_ROLE=standby. Verified control run:
https://github.com/Airshipster/rent-aggregator-baku/actions/runs/34767025281
It logged collector_role=standby primary_active=true and skipped collection.
This proves the healthy-primary path, not whole-server failover.

## Backup and rollback

Local backup: backups/lifecycle-20260913/database.dump (63,195,528 bytes).
SHA256 manifest and restore-verification.json are beside it. Restore into isolated
rent_restore_20260913 succeeded; cleanup fixture and unchanged users/payments
checked. Temporary DB dropped after testing; no dump stored on the server.
55 unit tests pass. Do not restore the full dump over newer user/payment data.

Rollback code: stop our watchdog timer and our collector/workers, repoint current
to releases/20260913-status-r3, then compose up only app/collector/channel-worker/
private-worker with that release's env and compose file; restart our timer.
Keep receipt table and newer data. Set GitHub role back to primary if reverting
server collection. Telegram deletions cannot be undone by changing an image;
do not replay old sends from a backup.

## Not claimed complete

- Public Bina push/subscription integration not found or enabled.
- Original creation time remains unverified; updatedAt can be a bump. The current
  internal latency uses first_seen_at in the listing DB, not original site time.
- Five-minute end-to-end SLA and full listing coverage need continuous evidence.
- No second host/replicated PostgreSQL: total host failure still stops delivery.
- Real failure takeover/recovery drill for GitHub remains to be performed.
- Pending historical cleanup drains gradually and is not finished on deployment.
- Media file_id cache is not implemented; no first-client/master forwarding.
- Full multilingual interactive filter UX acceptance remains unfinished.

## Proposed user menu

Main: Configure filter; My filters; Settings. Admin also sees System status.
Filter wizard: Deal -> rental period when relevant -> property -> location ->
price range -> review. Optional rooms/area/floor details can be opened from review.
Ranges use one screen with a manual range, presets, Any, Back and Confirm;
single value means exactly that value and is stated explicitly in the review.
Saved filter: summary, edit each basic field, additional conditions, pause,
delete with confirmation, back. Saving is explicit; back/cancel should not save.
Settings: Language, default city, notification preferences, access/payment.
Admin: requests, access management, System status, queues and incident details.
