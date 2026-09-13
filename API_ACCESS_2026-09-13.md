# Bina API access correction

Verified 2026-09-13, about 16:25 Baku, from the production collector container.
The normal client identity was retained; no cookies, proxies or WAF bypass used.

- POST https://bina.az/graphql returned HTTP 200 application/json for __typename.
- The existing itemsConnection query returned an actual listing (6457498).
- The prior HTML GET /kiraye returned Cloudflare 403. That did not establish
  that GraphQL was unavailable. The earlier whole-source diagnosis was too broad.
- Both current collectors unnecessarily fetched HTML before querying GraphQL.
  Removed that prerequisite; API 403 still aborts collection and backs off.
- Public partner API documentation was not found. FTL describes the platform's
  GraphQL implementation: https://fasterthanlight.me/projects/digital-classifieds

## Deployment

Only collector recreated using rent-aggregator-baku:20260913-api-r2.
Current release: /opt/Telegram-bots/bots/rent-aggregator-baku/releases/20260913-api-r2.
Its compose file pins this image for collector only. All other services retain r1.
No schema changes, no shared proxy/neighbor changes, no delivery gates changed.
Initial verification: six collector_spool records accepted into central storage;
collector heartbeat is in detail phase without an error. This is not an SLA proof.
36 local unit tests passed, including HTML independence and immediate API-403 stop.

Local source snapshot with read-back SHA256 manifest:
backups/api-preflight-20260913. Previous database restore evidence remains in
backups/deploy-20260913; no data migration performed by this patch.

Rollback: repoint current to releases/20260913-reliability-r1 and run docker compose
with project rent-aggregator-baku, that release's server/.env and
server/docker-compose.yml, up -d --no-deps collector. Do not restore the database.
This restores the former HTML dependency, so use only if the new code regresses.
