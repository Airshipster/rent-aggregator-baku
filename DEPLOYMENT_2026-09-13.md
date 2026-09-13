# Deployment verified on 2026-09-13

## Actual result

Release: `/opt/Telegram-bots/bots/rent-aggregator-baku/releases/20260913-reliability-r1`.
Image: `rent-aggregator-baku:20260913-r1`, digest
`sha256:adec68f447448f2eb211425e602bb1143ee7d11f3313ca8ff4773dc04b9ac9a4`.
Current points to this release. Previous release is
`20260815T030000Z-telegram-bots`. No neighboring bot or Traefik was restarted.

All app, postgres, channel-worker, private-worker and collector containers are
running. Healthcheck means the process responds, not that Bina collection works.

Production retention cancelled 1,874 channel sends and 14 private sends older than
seven days. Journal rows, identities, user registry and payment history preserved.
Younger historical sends remain held by the deployment cutoff, not bulk-released.
Channel policy: monthly rental apartments in Baku only. Private delivery mode is
admin_only until broader launch is explicitly approved. The admin currently has
zero enabled saved filters; no test filter was silently created.

Fresh copy: `backups/deploy-20260913/database.dump` on the owner's PC,
56,937,494 bytes. Manifest hashes, `retention-before.json` (targeted rollback), and
`restore-verification.json` are beside it. An explicitly authorized temporary
server database restored this dump fully, then was deleted. No server dump file
was created. Restored counts: 4 users, 0 payments, 47,234 listings, 120 deliveries,
124 private tasks, 11,081 channel posts, 11,126 channel tasks.

Verified on restored PostgreSQL: baseline, migration checksums, double migration,
retention idempotency, unchanged journal counts, committed claims, no double claim,
expiry at send, lost-response quarantine, 429 shared cooldown, crash recovery.
33 unit tests also passed. Admin `/start` through the real webhook returned 200
and produced one journalled menu. No friend/customer messages were sent.

Host timer `rent-aggregator-watchdog.timer` checks this bot every minute. An actual
private-worker stop/recovery test passed. Only its four named service containers
are in the restart allowlist. Operational alerts go only to the admin, at most
one combined alert in six hours. No Docker socket is mounted in bot containers.
The host scripts `watchdog.sh` and `operational_status.py` were installed after
the image build and run from the release directory by the host timer.

## Not solved by deployment

The server's source request still receives HTTP 403. Collector backs off 15 min;
it does not bypass restrictions. GitHub therefore remains the active collector,
NOT switched to standby yet. A dormant guarded standby path exists but has not
been end-to-end proven. Do not set COLLECTOR_ROLE=standby until permitted server
source access is working. Whole-server/database failure still stops delivery.

The five-minute target is NOT achieved or promised. GitHub cadence remains
best-effort. Source updatedAt/photo age are proxies, not proven creation time.
Operational alerts report these conditions instead of labelling the system ready
for paid customers. Independent failover, source agreement/access, immutable
historical source/filter evidence, removal coverage in the new collector,
uncertain-task reconciliation UI, independent filter drafts and seven-day SLA
measurement remain unfinished.

GitHub maintenance updates to Node24-capable actions follow their official
documentation: https://github.com/actions/checkout/blob/main/README.md and
https://github.com/actions/setup-python . They address runtime deprecation, not
Bina's 403. Collector workflow no longer receives Telegram or user-list secrets.

## Rollback constraints

Stop only `rent-aggregator-watchdog.timer` and this bot's workers/collector first.
Keep delivery disabled while rolling back code; old workers must NOT blindly
replay cancelled/uncertain tasks. Prefer a forward repair over schema rollback.
The full snapshot and exact retired-task states are local. Never overwrite newer
users/payments with an old dump; restore separately and reconcile first.
Never run `compose down -v`, restart shared Traefik, or alter SciTopus services.
