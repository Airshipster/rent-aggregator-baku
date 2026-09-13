#!/bin/sh
set -eu
# Host-side permission is confined by this fixed service allowlist, not user input.
root=/opt/Telegram-bots/bots/rent-aggregator-baku/current
for service in app collector channel-worker private-worker; do
    name="rent-aggregator-baku-${service}-1"
    running=$(docker inspect --format '{{.State.Running}}' "$name" 2>/dev/null || true)
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$name" 2>/dev/null || true)
    if [ "$running" != true ]; then
        docker compose --project-name rent-aggregator-baku --project-directory "$root/server" \
          --file "$root/server/docker-compose.yml" up -d --no-deps --no-build "$service"
    elif [ "$health" = unhealthy ]; then
        docker restart --timeout 30 "$name"
    fi
done
docker exec -i rent-aggregator-baku-app-1 python - < "$root/server/operational_status.py"
