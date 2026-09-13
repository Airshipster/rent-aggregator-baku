# Project Context: Rent Aggregator Baku

Last updated: 2026-09-13

## Latest: lifecycle and admin monitoring r4

Read LIFECYCLE_ROLLOUT_2026-09-13.md first. Release 20260913-lifecycle-r4 deployed;
migration 014 cleanup receipts. Local snapshot restored/tested and temporary DB
dropped. 55 tests passed. Admin System status is in main menu/settings. Alerts
are change-based. Channel cleanup deletes within Bot API 48-hour limit, otherwise
compacts; private rich messages edited in place (admin test passed). Journal
details compact after 14 days following confirmed cleanup; minimal dedupe keys
remain. 132 old payloads compacted; 286 legacy channel tasks queued, not all done.
50 statuses per GraphQL request, 90-second detail budget, 120-second cadence.
GitHub standby healthy-primary path verified in run 34767025281. Full outage
failover and five-minute source-publication SLA not proven; no public push API.

## Latest: listing status checks deployed

Release 20260913-status-r3 changes only collector. GitHub main commit 2de6d56.
Read LISTING_STATUS_2026-09-13.md. API and browser confirm manual closure of
6451158 and time expiry of 6113739 (despite isExpiredManually=false).
Shared parser now handles both; incomplete/error responses are not removal.
Server checks 10 previously delivered active listings per cycle with durable
cursor/spool. First 10-check pass succeeded at 16:53:39 Baku without errors.
47 unit tests passed. Whole archive recheck is gradual, not a five-minute promise.

## Latest: GraphQL access verified and collector corrected

At about 16:25 Baku on 2026-09-13, the existing /graphql endpoint returned
HTTP 200 from production for both a minimal query and real listing data.
HTML /kiraye 403 had incorrectly been treated as whole-source unavailability.
Removed the unused HTML prerequisite in both collectors; API refusal still stops
collection. Collector-only release 20260913-api-r2 is current; other services keep
r1. Initial 64 payloads accepted into PostgreSQL. GitHub main includes fix 86b7130
via merge 4b6136f. Read API_ACCESS_2026-09-13.md. Five-minute SLA remains unproven.

## Earlier deployment report (source diagnosis superseded above)

Read `DEPLOYMENT_2026-09-13.md` first; it supersedes the earlier not-deployed
snapshot below. Owner explicitly authorized server restore and deployment.
Code committed/pushed in `b4e0e61` from isolated worktree based on latest main;
original working tree untouched. Control run `34735923269` also failed with source
HTTP 403 (07:37 Baku), so GitHub is enabled but NOT currently verified working.
Full restore and PostgreSQL failure tests passed; temporary DB was deleted.
Release `20260913-reliability-r1` is live, migrations 001-013 versioned.
1,874 channel + 14 private old send tasks cancelled, journals retained.
All five own containers running. Own one-minute watchdog recovery tested.
Real admin /start test succeeded; no enabled admin filters currently exist.
Private sends remain admin_only; new channel sends use monthly/Baku/apartments
policy and deployment cutoff. Younger backlog is not flooded.
Source still returns 403 on server; GitHub stays primary. Five-minute SLA is NOT
achieved. Do not call this production commercially ready. Remaining work and
rollback constraints are listed in the deployment report.

## Reliability implementation, later on 2026-09-13 (NOT DEPLOYED)

Latest decisions override the earlier audit: channel is MONTHLY rental apartments
in Baku only. Cancel pending sends older than seven days, but preserve journal and
deduplication records. Applies to channel and personal deliveries. Admin-only test
delivery is authorized; friend/customer test broadcasts are not.

Read `RELIABILITY_ROLLOUT_2026-09-13.md` before deployment. New local components:
versioned migrations, cancellation retention, short committed outbox claims,
attempt log/uncertain quarantine, shared 429 cooldown, PostgreSQL-backed collector
discovery/spool, guarded GitHub standby and bot-specific host watchdog.
33 unit tests pass; SQL integration and restore verification have NOT passed.

Fresh local backup: `backups/pre-reliability-20260913/database.dump`, 56,937,494
bytes, owner/SYSTEM ACL. Download-only capture; not uploaded to server. Windows
Smart App Control blocks official EDB PostgreSQL 16.15 unsigned initdb (Code
Integrity events 3118/3077, exit 3236495362). Do not disable Windows protection.
Asked owner permission for temporary isolated server restore; waiting for answer.
No production migration, retention cancellation, release switch or Telegram test
was performed. Existing workers are still absent.

Live ordinary source request from server returned HTTP 403. This is a separate
blocker from GitHub scheduling and missing workers. Do not claim 5-minute SLA or
route around source denial. A permitted reliable source feed/access is needed.
Three unread repo-specific Gmail failure notices were read and marked read;
follow-up exact-repo unread search returned zero. Other emails were untouched.

## Verified audit state: 2026-09-13

Read `TECHNICAL_AUDIT_2026-09-13.md` before further work. Sections below are the
historical baseline where they conflict with this verified snapshot.

- Intended product: national/all-category personal filters; public channel only
  monthly rental apartments in Baku (confirmed in the later owner decision).
- App and PostgreSQL are healthy, but neither delivery worker container exists.
  Compose still defines both. Do not start them blindly: 2519 channel send tasks
  and 5 removal tasks are pending. Private queue has 15 tasks for one non-admin.
- Last channel delivery: 2026-08-24 01:09:26 Asia/Baku. Last private delivery:
  2026-08-15 06:56:53. Ingest still works (verified 2026-09-13 05:06:54 Baku).
- Last 100 Actions starts have median spacing 189.2 minutes, not five minutes.
  Three latest failures on September 11-12 are source HTTP 403. Node warning is separate.
- Local fixes and 24 passing unit tests exist; NOTHING from this audit was deployed
  or pushed. No test Telegram sends, deletions or user broadcasts were performed.
- New worker candidate defaults to DELIVERY_ENABLED=false and requires an explicit
  timezone-aware DELIVERY_NOT_BEFORE. Migration 012 adds dead_letter, not applied.
- Local UX candidate uses one range screen with explicit apply, additional floors,
  and confirmation before today's backfill. Today means observed today, not
  confirmed source creation time. Independent filter drafts remain to be implemented.
- Full source/filter history, crash-safe uncertain sends, integration/E2E tests,
  restore verification and seven-day observation are NOT complete.
- Fresh local snapshot: backups/audit-20260913T0210, manifest and pg_restore catalog
  verified. Full restore is NOT verified. Backup ACL is restricted to owner/SYSTEM.
- Shared /opt/Telegram-bots, Traefik and neighboring bots must not be modified.
  No permanent backup files were created on the server.


## Local project

- Path: `C:\Users\Animus\Desktop\Codex\rent agregator baku`
- GitHub repository: `https://github.com/Airshipster/rent-aggregator-baku.git`
- Main purpose: collect Bina.az listings and deliver matching Baku rental-apartment listings to Telegram users and the public channel.

## Current architecture

- GitHub Actions runs the collector on the `rent-monitor` workflow, currently scheduled every five minutes.
- The collector sends signed, idempotent batches to the central server; it is not the permanent Telegram transport.
- Production root on the server: `/opt/Telegram-bots/bots/rent-aggregator-baku`.
- The active server release runs as separate app, private-worker, channel-worker, and PostgreSQL containers.
- Public webhook: `https://scitopus.com/telegram-bots/rent-aggregator-baku/webhook`.
- Ingest endpoint: `https://scitopus.com/telegram-bots/rent-aggregator-baku/v1/ingest/listings`.

## Delivery and deduplication

- PostgreSQL is the source of truth for listings, users, filters, deliveries, channel posts, payments, updates, and audit records.
- Private and channel deliveries use separate outbox tables and workers.
- Delivery tasks have pending, processing, sent, and failed states, retry timestamps, attempts, and stale-lock recovery.
- Ingest is idempotent by request key. Listings are unique by source and source listing ID; private delivery is unique by listing and Telegram user; channel publication is unique by listing.
- Telegram retry-after responses are delayed before retry. There is currently no terminal dead-letter queue; failed tasks remain retryable.

## Freshness rules

- Private notifications normally use a 24-hour freshness window.
- The public channel is restricted to Baku rental apartments: new-build and old-build apartment categories, monthly or daily rent.
- The public channel currently allows a wider seven-day window. The source date is taken from the first photo URL when parseable, with `updatedAt` as a fallback.
- The first-photo timestamp is a proxy, not an authoritative Bina publication timestamp. A future strict mode should reject listings when neither a reliable publication date nor a parseable photo date exists.
- Public posts do not expose seller name, phone number, full description, coordinates, Google Maps URL, or an unnecessarily precise address.
- Media is split into batches of at most ten photos; odd batches put the extra photo in the first batch.

## Source audit: 2026-08-19

The folder `C:\Users\Animus\Documents\Codex\2026-07-03` was inspected. It contains only a separate `f` project for FOBO luxury-real-estate branding. It has Playwright scripts, logo-reference downloads, SVG concepts, browser profiles, screenshots, contact sheets, and generator experiments, but no Rent Aggregator code or dependency.

No files from that folder were copied into this repository. The original context file was read from:

`C:\Users\Animus\Documents\Codex\2026-05-16\c-users-choob-desktop-codex\PROJECT_CONTEXT_rent-agregator-baku.md`

Its historical information was consolidated here; the original file was not modified or deleted.

## Secrets and safety

- Never store or print real bot tokens, user IDs, chat IDs, passwords, or signed ingest values in source or context files.
- Do not bypass CAPTCHA, Cloudflare challenges, rate limits, or other anti-bot protections.
- Do not use Playwright or proxies for the collector unless explicitly approved for a defined safe diagnostic.
- Do not commit or push changes unless explicitly requested.
