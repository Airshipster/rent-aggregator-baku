# Telegram-bots server layout

The shared server root is `/opt/Telegram-bots`. It is a neutral hosting boundary,
not a Rent Aggregator Baku project directory.

```text
/opt/Telegram-bots/
  bots/
    rent-aggregator-baku/  # this bot only
    scitopus/              # reserved for the independent SciTopus deployment
  shared/
    README.md              # neutral operating rules only
```

Each bot owns its source tree, Compose project, environment file, PostgreSQL
database/volume, workers, logs, routes, Telegram token, webhook secret, ingest
secret and rate limits. Bots may share only the host, Docker runtime, the
external `traefik` network and generic monitoring conventions.

Rent Aggregator Baku routes:

- webhook: `/telegram-bots/rent-aggregator-baku/webhook`
- ingest: `/telegram-bots/rent-aggregator-baku/v1/ingest/listings`

Legacy routes remain temporary compatibility aliases during cutover. A future
SciTopus deployment must use its own `/telegram-bots/scitopus/...` routes and
must not reference Rent Aggregator Baku service, route, volume, database or
environment names.

## Rollback

Before a production cutover, create and restore-test a PostgreSQL custom-format
dump and archive the active release plus environment file with restricted
permissions. Transfer verified backup artifacts to the owner's computer and
remove the server copies; the server is not a backup store. Keep the old
`/opt/rent-aggregator-baku` entry as a compatibility symlink. Rollback consists
of stopping the new Compose project, restoring the release and database from
the local backup when needed, starting Compose and restoring the previous
Telegram webhook URL.
