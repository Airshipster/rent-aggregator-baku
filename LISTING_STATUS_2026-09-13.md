# Listing status verification

Live API and browser checks, 2026-09-13 (Baku).

| Listing | isExpiredManually | expiresAt | Result |
| --- | --- | --- | --- |
| https://bina.az/items/6451158 | true | 2026-09-11T16:28:40+04:00 | closed; visible site label Kiraye verilib (rented) |
| https://bina.az/items/6113739 | false | 2026-06-07T23:24:19+04:00 | expired; browser explicitly shows expiry at this time |
| https://bina.az/items/6457498 | false | null | active according to API at check time |

Additional API samples 6451029, 6445326, 6438928 and 6447573 all returned
isExpiredManually=true. No real item:null example found in this small sample;
the explicit-null branch is covered by a synthetic test, not live evidence.

Previous code checked only isExpiredManually and misclassified timed expiry.
Both check_exists and full-detail parsing now share the status classifier.
Missing fields, wrong IDs, malformed dates, HTTP/network/GraphQL errors are not
removal evidence. An explicit item:null in a successful query means unavailable,
not proof of a physical deletion or a completed rental/sale.

The server collector now rechecks up to 10 previously delivered, still-active
Bina listings per cycle, preserving a PostgreSQL round-robin cursor. Confirmed
inactive status passes through durable collector_spool and existing idempotent
mark_removed queues; no physical data deletion. This bounded pass does not
guarantee every old post will be checked within five minutes.

47 local tests pass. Collector-only rollout target: 20260913-status-r3, image
rent-aggregator-baku:20260913-status-r3. No schema migration; other containers
retain their images. Local source snapshot: backups/listing-status-20260913.
Rollback: select the previous 20260913-api-r2 release and recreate only collector
using that release's compose/env and project rent-aggregator-baku. Do not restore
the entire DB or replay old delivery tasks. Already edited Telegram posts are not
reversed by an image rollback.
