# Rent Aggregator Baku

Личный мониторинг свежих объявлений аренды. GitHub Actions запускает скрипт каждые 5 минут, отправляет подробную карточку владельцу в Telegram и опционально короткий пост в небольшой канал.

Публичный пост не содержит телефон, имя продавца, полное описание, координаты, Google Maps и не перезаливает фотографии. В личку отправляется подробная версия без телефона.

## Что нужно

1. Создайте Telegram bot через BotFather.
2. Добавьте бота в личный чат, публичный или приватный канал для коротких постов и отдельный приватный state-чат.
3. В канале дайте боту право публиковать сообщения.
4. В state-чате дайте боту право отправлять, редактировать и закреплять сообщения.
5. Получите `OWNER_USER_ID` через любого ID-бота или через `getUpdates`.
6. Получите `OWNER_CHAT_ID`, написав боту и посмотрев `chat.id` через `getUpdates`.
7. Добавьте в GitHub Secrets:

```txt
TELEGRAM_BOT_TOKEN
TELEGRAM_OWNER_CHAT_ID
TELEGRAM_OWNER_USER_ID
TELEGRAM_PUBLIC_CHANNEL_ID
TELEGRAM_STATE_CHAT_ID
SOURCE_START_URL
SOURCE_GRAPHQL_PATH
```

`SOURCE_GRAPHQL_PATH` обычно задаётся как `/graphql`.

## Переменные репозитория

Добавьте Repository Variables при необходимости:

```txt
ENABLE_PUBLIC_CHANNEL=false
ENABLE_PRIVATE_FULL=true
PUBLIC_LANGUAGE=az
PRIVATE_LANGUAGE=ru
MAX_LISTINGS_PER_RUN=20
MAX_DETAIL_FETCHES_PER_RUN=10
MAX_IMAGES_PRIVATE=50
DRY_RUN=false
REQUEST_TIMEOUT_SECONDS=20
PROTECT_PRIVATE_CONTENT=true
MAX_NEW_AGE_HOURS=24
UPDATE_SCAN_HOURS=168
UPDATE_CHECK_INTERVAL_MINUTES=60
```

На первом запуске удобно поставить `DRY_RUN=true`, проверить логи, затем переключить на `false`.

## Запуск

1. Откройте вкладку Actions.
2. Выберите workflow `rent-monitor`.
3. Нажмите `Run workflow`.
4. После проверки включите schedule. Cron уже задан как `*/5 * * * *`.

## State

Основной state хранится в закрепленном JSON-сообщении в приватном state-чате. В state нет фото, описаний, HTML и телефонов.

Если pinned state недоступен, используется fallback-файл:

```txt
state/last_seen.json
```

Он хранит только ID, URL, время обновления и последние ID для защиты от дублей.

## Команды

Команды принимает только владелец по `TELEGRAM_OWNER_USER_ID`.

```txt
/start
/status
/dryrun
/pause
/resume
/setlast 1234567
```

Если кто-то другой пишет боту, бот отвечает `Bot aktiv deyil.`. Если бота добавляют в чужой чат, он выходит из чата.

## Правила публикации

Новые объявления публикуются только если они выглядят свежими за последние 24 часа. Скрипт проверяет время обновления и, когда доступно, дату первой фотографии как дополнительный фильтр против старых поднятых объявлений. Это защищает от массовой публикации старых объявлений после сбоя или позднего перезапуска.

Раз в час скрипт проверяет последние сохранённые объявления за неделю. Если объявление больше не активно, он может отправить короткий update с ❌.

## Безопасность

Скрипт не запрашивает телефонные поля, не нажимает кнопки, не использует прокси, не использует Playwright и не обходит CAPTCHA, Cloudflare challenge или rate-limit. При признаках блокировки выполнение останавливается.
