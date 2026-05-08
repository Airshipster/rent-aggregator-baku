import os
from datetime import timedelta

from .formatter_private_ru import format_private
from .formatter_public_az import format_deleted_update, format_public
from .models import ListingDetail, ListingSummary, RunStats
from .source_client import SourceBlockedError, SourceClient
from .source_parser import SourceParser
from .state import StateStore
from .telegram_client import TelegramClient
from .utils import env_bool, env_int, image_datetime, is_recent, now_utc, parse_dt, sleep_soft


def main() -> None:
    stats = RunStats()
    dry_run = env_bool("DRY_RUN", False)
    telegram = None if dry_run and not os.getenv("TELEGRAM_BOT_TOKEN") else TelegramClient()
    state_store = StateStore(telegram)
    state = state_store.load()
    process_commands(telegram, state, state_store, dry_run)
    if state.get("paused"):
        print("paused=true")
        return
    try:
        client = SourceClient()
        parser = SourceParser(client)
        client.get_start_page()
        summaries = load_candidate_summaries(parser, state)
        stats.found = len(summaries)
        stats.last_seen_id = state.get("last_seen_listing_id")
        publish_new(parser, telegram, state, state_store, summaries, stats, dry_run)
        run_update_check(parser, telegram, state, state_store, stats, dry_run)
    except SourceBlockedError as exc:
        stats.errors += 1
        stats.messages.append(str(exc))
    except Exception as exc:
        stats.errors += 1
        stats.messages.append(type(exc).__name__)
    print_summary(stats)


def load_candidate_summaries(parser: SourceParser, state: dict) -> list[ListingSummary]:
    max_per_run = env_int("MAX_LISTINGS_PER_RUN", 20)
    first_page = parser.list_recent(max_per_run, pages=1)
    last_seen = state.get("last_seen_listing_id")
    if not last_seen or any(item.listing_id == last_seen for item in first_page):
        return first_page
    return parser.list_recent(max_per_run, pages=3)


def publish_new(
    parser: SourceParser,
    telegram: TelegramClient | None,
    state: dict,
    state_store: StateStore,
    summaries: list[ListingSummary],
    stats: RunStats,
    dry_run: bool,
) -> None:
    last_seen = state.get("last_seen_listing_id")
    max_details = env_int("MAX_DETAIL_FETCHES_PER_RUN", 10)
    max_age = max(env_int("MAX_PRIVATE_AGE_HOURS", env_int("MAX_NEW_AGE_HOURS", 24)), env_int("MAX_PUBLIC_AGE_HOURS", 168))
    candidates = []
    seen = set()
    for item in summaries:
        if item.listing_id in seen:
            continue
        seen.add(item.listing_id)
        if item.listing_id == last_seen:
            break
        if not is_recent(item.updated_at, max_age):
            stats.skipped_old += 1
            continue
        candidates.append(item)
        if len(candidates) >= max_details:
            break
    candidates.reverse()
    stats.new_count = 0
    for summary in candidates:
        sleep_soft()
        try:
            detail = parser.get_detail(summary.listing_id)
            if not detail or detail.is_deleted:
                continue
            photo_dt = image_datetime(detail.first_image_url)
            if photo_dt and not is_recent(photo_dt, max_age):
                stats.skipped_old += 1
                continue
            delivered = deliver_listing(telegram, detail, dry_run, stats)
            if delivered:
                stats.new_count += 1
            if delivered and not dry_run:
                remember_listing(state, detail)
                state["last_seen_listing_id"] = detail.listing_id
                state["last_seen_listing_url"] = detail.listing_url
                state_store.save(state)
        except Exception as exc:
            stats.errors += 1
            stats.messages.append(f"{summary.listing_id}:{type(exc).__name__}")


def deliver_listing(telegram: TelegramClient | None, item: ListingDetail, dry_run: bool, stats: RunStats) -> bool:
    private_enabled = env_bool("ENABLE_PRIVATE_FULL", True)
    public_enabled = env_bool("ENABLE_PUBLIC_CHANNEL", False)
    private_recent = is_recent(item.updated_at, env_int("MAX_PRIVATE_AGE_HOURS", 24))
    public_recent = is_recent(image_datetime(item.first_image_url) or item.updated_at, env_int("MAX_PUBLIC_AGE_HOURS", 168))
    delivered = False
    if dry_run:
        print(f"DRY_RUN new {item.listing_id}")
        return True
    if telegram is None:
        return False
    if private_enabled and private_recent:
        try:
            owner_chat_id = os.environ["TELEGRAM_OWNER_CHAT_ID"]
            telegram.send_message(owner_chat_id, "______Следующее_объявление______", protect_content=telegram.protect)
            telegram.send_long_message(owner_chat_id, format_private(item), protect_content=telegram.protect)
            if item.latitude and item.longitude:
                telegram.send_location(owner_chat_id, item.latitude, item.longitude, protect_content=telegram.protect)
            telegram.send_photos(owner_chat_id, item.image_urls, item.listing_id, env_int("MAX_IMAGES_PRIVATE", 50))
            stats.private_sent += 1
            delivered = True
        except Exception as exc:
            stats.errors += 1
            stats.messages.append(f"private:{item.listing_id}:{type(exc).__name__}")
    if public_enabled and public_recent:
        try:
            channel_id = os.environ["TELEGRAM_PUBLIC_CHANNEL_ID"]
            message = telegram.send_message(channel_id, format_public(item), link_preview_url=item.listing_url)
            _ = message.get("message_id")
            stats.public_sent += 1
            delivered = True
        except Exception as exc:
            stats.errors += 1
            stats.messages.append(f"public:{item.listing_id}:{type(exc).__name__}")
    return delivered

def remember_listing(state: dict, item: ListingDetail) -> None:
    recent = [entry for entry in state.get("recent_listings", []) if entry.get("listing_id") != item.listing_id]
    recent.append(
        {
            "listing_id": item.listing_id,
            "listing_url": item.listing_url,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
    )
    state["recent_listings"] = recent[-100:]


def run_update_check(
    parser: SourceParser,
    telegram: TelegramClient | None,
    state: dict,
    state_store: StateStore,
    stats: RunStats,
    dry_run: bool,
) -> None:
    interval = env_int("UPDATE_CHECK_INTERVAL_MINUTES", 60)
    last = parse_dt(state.get("last_update_check_at"))
    if last and last > now_utc() - timedelta(minutes=interval):
        return
    state["last_update_check_at"] = now_utc().isoformat()
    public_enabled = env_bool("ENABLE_PUBLIC_CHANNEL", False)
    week_hours = env_int("UPDATE_SCAN_HOURS", 168)
    notified = set(state.get("deleted_notified_ids") or [])
    checked = 0
    for entry in list(state.get("recent_listings") or []):
        if checked >= 10:
            break
        if entry.get("listing_id") in notified:
            continue
        if not is_recent(parse_dt(entry.get("updated_at")), week_hours):
            continue
        checked += 1
        try:
            exists = parser.check_exists(entry["listing_id"])
            if not exists:
                if dry_run:
                    print(f"DRY_RUN deleted {entry['listing_id']}")
                elif telegram and public_enabled:
                    telegram.send_message(os.environ["TELEGRAM_PUBLIC_CHANNEL_ID"], format_deleted_update(entry.get("listing_url") or "", entry["listing_id"]))
                notified.add(entry["listing_id"])
                stats.updates_sent += 1
        except Exception as exc:
            stats.errors += 1
            stats.messages.append(f"update:{entry.get('listing_id')}:{type(exc).__name__}")
        sleep_soft()
    state["deleted_notified_ids"] = list(notified)[-100:]
    if not dry_run:
        state_store.save(state)


def process_commands(telegram: TelegramClient | None, state: dict, state_store: StateStore, dry_run: bool) -> None:
    if telegram is None or dry_run:
        return
    owner_user_id = str(os.environ["TELEGRAM_OWNER_USER_ID"])
    allowed_chats = {str(os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")), str(os.environ.get("TELEGRAM_PUBLIC_CHANNEL_ID", "")), str(os.environ.get("TELEGRAM_STATE_CHAT_ID", ""))}
    approved_users = {str(x) for x in state.get("approved_user_ids", [])}
    pending_users = {str(x) for x in state.get("pending_user_ids", [])}
    offset = state.get("update_offset")
    try:
        updates = telegram.get_updates(offset)
    except Exception:
        return
    for update in updates:
        state["update_offset"] = update["update_id"] + 1
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        user = message.get("from") or {}
        user_id = str(user.get("id") or "")
        text = (message.get("text") or "").strip()
        if chat_id and chat_id not in allowed_chats and chat.get("type") != "private":
            try:
                telegram.leave_chat(chat_id)
            except Exception:
                pass
            continue
        if user_id != owner_user_id and user_id not in approved_users:
            if chat.get("type") == "private" and chat_id:
                if user_id and user_id not in pending_users:
                    pending_users.add(user_id)
                    state["pending_user_ids"] = sorted(pending_users)
                    name = " ".join(x for x in [user.get("first_name"), user.get("last_name"), user.get("username")] if x)
                    try:
                        telegram.send_message(
                            os.environ["TELEGRAM_OWNER_CHAT_ID"],
                            f"Новый пользователь просит доступ:\nuser_id={user_id}\nchat_id={chat_id}\n{name}\n\nОдобрить: /approve {user_id}\nОтклонить: /deny {user_id}",
                        )
                    except Exception:
                        pass
                try:
                    telegram.send_message(chat_id, "Sorğu göndərildi.")
                except Exception:
                    pass
            continue
        if text == "/start":
            telegram.send_message(chat_id, "OK")
        elif text == "/status":
            telegram.send_message(chat_id, f"last_seen_id={state.get('last_seen_listing_id')}\nupdated_at={state.get('updated_at')}\npaused={state.get('paused')}")
        elif text == "/dryrun":
            telegram.send_message(chat_id, "DRY_RUN GitHub Actions env ilə idarə olunur.")
        elif text == "/pause":
            state["paused"] = True
            telegram.send_message(chat_id, "Paused")
        elif text == "/resume":
            state["paused"] = False
            telegram.send_message(chat_id, "Resumed")
        elif text.startswith("/setlast "):
            listing_id = text.split(maxsplit=1)[1].strip()
            state["last_seen_listing_id"] = listing_id
            state["last_seen_listing_url"] = None
            telegram.send_message(chat_id, f"Set last_seen_id={listing_id}")
        elif text.startswith("/approve "):
            approved_id = text.split(maxsplit=1)[1].strip()
            approved_users.add(approved_id)
            pending_users.discard(approved_id)
            state["approved_user_ids"] = sorted(approved_users)
            state["pending_user_ids"] = sorted(pending_users)
            telegram.send_message(chat_id, f"Approved {approved_id}")
        elif text.startswith("/deny "):
            denied_id = text.split(maxsplit=1)[1].strip()
            pending_users.discard(denied_id)
            state["pending_user_ids"] = sorted(pending_users)
            telegram.send_message(chat_id, f"Denied {denied_id}")
    state_store.save(state)


def print_summary(stats: RunStats) -> None:
    print(f"found={stats.found}")
    print(f"last_seen_id={stats.last_seen_id}")
    print(f"new={stats.new_count}")
    print(f"private_sent={stats.private_sent}")
    print(f"public_sent={stats.public_sent}")
    print(f"updates_sent={stats.updates_sent}")
    print(f"skipped_old={stats.skipped_old}")
    print(f"errors={stats.errors}")
    for message in stats.messages[:20]:
        print(f"note={message}")


if __name__ == "__main__":
    main()
