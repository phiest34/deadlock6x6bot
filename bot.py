import asyncio
import logging
import os
import random
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from deadlock_data import GENERAL_TIPS, HEROES
from storage import FriendRepository, create_friend_repository
from steam_monitor import (
    DeadlockApiClient,
    SteamApiClient,
    format_friend_status,
    format_transition_message,
    is_in_deadlock,
    normalize_public_user_reference,
    public_id_from_player,
    safe_get_active_matches,
    safe_get_friend_list,
    safe_get_hero_map,
    safe_get_match_history,
    safe_get_player_hero_stats,
    safe_get_player_mmr,
    safe_get_player_summaries,
    safe_resolve_user_reference,
    steam_id64_to_account_id,
)


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("deadbot")

DEFAULT_POLL_INTERVAL = 60
RANK_DIVISION_NAMES = {
    0: "Obscurus",
    1: "Initiate",
    2: "Seeker",
    3: "Alchemist",
    4: "Arcanist",
    5: "Ritualist",
    6: "Emissary",
    7: "Archon",
    8: "Oracle",
    9: "Phantom",
    10: "Ascendant",
    11: "Eternus",
}


@dataclass
class BotConfig:
    steam_api_key: Optional[str]
    poll_interval_seconds: int


def normalize_hero_name(name: str) -> str:
    return name.strip().lower()


def render_hero_message(hero_name: str) -> Optional[str]:
    hero_data = HEROES.get(hero_name)

    if not hero_data:
        return None

    tip_lines = "\n".join(f"- {tip}" for tip in hero_data["tips"])
    return (
        f"*{hero_name.title()}*\n"
        f"Роль: {hero_data['role']}\n"
        f"{hero_data['summary']}\n\n"
        f"Советы:\n{tip_lines}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = (
        "Я бот по Deadlock.\n"
        "Команды:\n"
        "/hero <герой> - краткая справка по герою\n"
        "/tip - случайный общий совет\n"
        "/addfriend <steam vanity/link/id> [псевдоним] - добавить игрока в мониторинг\n"
        "/importfriends <steam vanity/link/id> - добавить всех публичных друзей профиля\n"
        "/removefriend <steam vanity/link/id> - убрать игрока из мониторинга\n"
        "/profile <steam vanity/link/id> - краткий профиль игрока\n"
        "/heroes <steam vanity/link/id> [alltime|recent] - топ героев игрока\n"
        "/live <steam vanity/link/id> - best-effort live-информация о текущем матче\n"
        "/friends - список отслеживаемых игроков\n"
        "/check - проверить статусы прямо сейчас\n"
        "/helpme - список команд"
    )
    await update.message.reply_text(message)


async def hero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text("Использование: /hero <имя героя>")
        return

    requested_name = " ".join(context.args)
    hero_name = normalize_hero_name(requested_name)
    message = render_hero_message(hero_name)

    if not message:
        known_heroes = ", ".join(sorted(HEROES))
        await update.message.reply_text(
            f"Не знаю героя `{requested_name}`. Сейчас доступны: {known_heroes}.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(message, parse_mode="Markdown")


async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not update.message:
        return
    await update.message.reply_text(random.choice(GENERAL_TIPS))


async def helpme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not update.message:
        return
    message = (
        "Команды:\n"
        "/hero <герой> - краткая справка по герою\n"
        "/tip - случайный общий совет\n"
        "/addfriend <steam vanity/link/id> [псевдоним] - добавить игрока в мониторинг\n"
        "/importfriends <steam vanity/link/id> - добавить всех публичных друзей профиля\n"
        "/removefriend <steam vanity/link/id> - убрать игрока из мониторинга\n"
        "/profile <steam vanity/link/id> - краткий профиль игрока\n"
        "/heroes <steam vanity/link/id> [alltime|recent] - топ героев игрока\n"
        "/live <steam vanity/link/id> - best-effort live-информация о текущем матче\n"
        "/friends - список отслеживаемых игроков\n"
        "/check - проверить статусы прямо сейчас\n"
        "/helpme - список команд"
    )
    await update.message.reply_text(message)


def get_store(context: ContextTypes.DEFAULT_TYPE) -> FriendRepository:
    return context.application.bot_data["friend_store"]


def get_config(context: ContextTypes.DEFAULT_TYPE) -> BotConfig:
    return context.application.bot_data["config"]


def get_steam_client(context: ContextTypes.DEFAULT_TYPE) -> Optional[SteamApiClient]:
    return context.application.bot_data.get("steam_client")


def get_deadlock_client(context: ContextTypes.DEFAULT_TYPE) -> DeadlockApiClient:
    return context.application.bot_data["deadlock_client"]


def monitoring_enabled(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(get_config(context).steam_api_key)


async def addfriend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    if not monitoring_enabled(context):
        await update.message.reply_text("Мониторинг Steam выключен: не задан STEAM_API_KEY.")
        return

    if not context.args:
        await update.message.reply_text(
            "Использование: /addfriend <steam vanity/link/id> [псевдоним]"
        )
        return

    steam_ref = context.args[0].strip()
    alias = " ".join(context.args[1:]).strip() or None
    steam_client = get_steam_client(context)
    if not steam_client:
        await update.message.reply_text("Steam API клиент не инициализирован.")
        return

    steam_id = await safe_resolve_user_reference(steam_client, steam_ref)
    if not steam_id:
        await update.message.reply_text(
            "Не удалось распознать игрока. Пришли vanity, vanity URL или ссылку Steam-профиля."
        )
        return

    public_id = normalize_public_user_reference(steam_ref) or alias
    store = get_store(context)
    store.add_friend(update.effective_chat.id, steam_id, public_id, alias)
    label = alias or public_id or "пользователь"
    await update.message.reply_text(f"Добавил в мониторинг: {label}.")


async def removefriend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    if not context.args:
        await update.message.reply_text("Использование: /removefriend <steam vanity/link/id>")
        return

    steam_ref = context.args[0].strip()
    steam_client = get_steam_client(context)
    if not steam_client:
        await update.message.reply_text("Steam API клиент не инициализирован.")
        return

    steam_id = await safe_resolve_user_reference(steam_client, steam_ref)
    if not steam_id:
        await update.message.reply_text(
            "Не удалось распознать игрока. Пришли vanity, vanity URL или ссылку Steam-профиля."
        )
        return

    store = get_store(context)
    removed_count = store.remove_friend(update.effective_chat.id, steam_id)
    if removed_count == 0:
        await update.message.reply_text("Такого игрока нет в списке этого чата.")
        return

    public_id = normalize_public_user_reference(steam_ref) or "игрок"
    await update.message.reply_text(f"Убрал из мониторинга: {public_id}.")


async def importfriends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    if not monitoring_enabled(context):
        await update.message.reply_text("Мониторинг Steam выключен: не задан STEAM_API_KEY.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /importfriends <steam vanity/link/id>")
        return

    steam_ref = context.args[0].strip()
    steam_client = get_steam_client(context)
    if not steam_client:
        await update.message.reply_text("Steam API клиент не инициализирован.")
        return

    owner_steam_id = await safe_resolve_user_reference(steam_client, steam_ref)
    if not owner_steam_id:
        await update.message.reply_text(
            "Не удалось распознать профиль. Пришли vanity, vanity URL или ссылку Steam-профиля."
        )
        return

    friend_ids = await safe_get_friend_list(steam_client, owner_steam_id)
    if not friend_ids:
        await update.message.reply_text(
            "Не удалось получить список друзей. Скорее всего friends list у профиля не публичный."
        )
        return

    players = await safe_get_player_summaries(steam_client, friend_ids)
    store = get_store(context)
    imported_count = 0
    for steam_id in friend_ids:
        player = players.get(steam_id)
        public_id = public_id_from_player(player)
        alias = player.get("personaname") if player else None
        store.add_friend(update.effective_chat.id, steam_id, public_id, alias)
        imported_count += 1

    source_label = normalize_public_user_reference(steam_ref) or "профиль"
    await update.message.reply_text(
        f"Добавил в мониторинг {imported_count} друзей из профиля {source_label}."
    )


def format_duration_compact(total_seconds: Optional[int]) -> Optional[str]:
    if total_seconds is None:
        return None
    total_seconds = max(0, int(total_seconds))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def find_player_in_active_match(active_match: dict, account_id: int) -> Optional[dict]:
    for player in active_match.get("players", []):
        if player.get("account_id") == account_id:
            return player
    return None


def resolve_display_name(steam_ref: str, player_summary: Optional[dict]) -> str:
    return (
        normalize_public_user_reference(steam_ref)
        or (player_summary.get("personaname") if player_summary else None)
        or "игрок"
    )


def hero_name_for_id(hero_map: dict[int, str], hero_id: Optional[int]) -> str:
    if hero_id is None:
        return "Unknown hero"
    return hero_map.get(hero_id, f"Hero ID {hero_id}")


def format_percent(value: float) -> str:
    return f"{value:.1f}%"


def format_result_icon(match_result: Optional[int]) -> str:
    if match_result == 1:
        return "W"
    if match_result == 0:
        return "L"
    return "?"


def summarize_recent_heroes(matches: list[dict]) -> dict[int, dict[str, int]]:
    summary: dict[int, dict[str, int]] = {}
    for match in matches:
        hero_id = match.get("hero_id")
        if hero_id is None:
            continue
        hero_bucket = summary.setdefault(int(hero_id), {"matches": 0, "wins": 0})
        hero_bucket["matches"] += 1
        if match.get("match_result") == 1:
            hero_bucket["wins"] += 1
    return summary


def format_rank_name(division: Optional[int], division_tier: Optional[int]) -> Optional[str]:
    if division is None or division_tier is None:
        return None
    rank_name = RANK_DIVISION_NAMES.get(int(division))
    if not rank_name:
        return None
    return f"{rank_name} {division_tier}"


async def resolve_player_context(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[Optional[str], Optional[str], Optional[int], Optional[dict]]:
    if not update.message:
        return None, None, None, None

    if not context.args:
        return None, None, None, None

    steam_client = get_steam_client(context)
    if not steam_client:
        await update.message.reply_text("Steam API клиент не инициализирован.")
        return None, None, None, None

    steam_ref = context.args[0].strip()
    steam_id = await safe_resolve_user_reference(steam_client, steam_ref)
    if not steam_id:
        await update.message.reply_text(
            "Не удалось распознать игрока. Пришли vanity, vanity URL или ссылку Steam-профиля."
        )
        return None, None, None, None

    account_id = steam_id64_to_account_id(steam_id)
    if account_id is None:
        await update.message.reply_text("Не удалось вычислить account_id игрока.")
        return None, None, None, None

    player_summary_map = await safe_get_player_summaries(steam_client, [steam_id])
    player_summary = player_summary_map.get(steam_id)
    display_name = resolve_display_name(steam_ref, player_summary)
    return steam_id, display_name, account_id, player_summary


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text("Использование: /profile <steam vanity/link/id>")
        return

    _, display_name, account_id, _ = await resolve_player_context(update, context)
    if account_id is None or display_name is None:
        return

    deadlock_client = get_deadlock_client(context)
    mmr_rows = await safe_get_player_mmr(deadlock_client, [account_id])
    hero_stats = await safe_get_player_hero_stats(deadlock_client, [account_id])
    recent_matches = await safe_get_match_history(deadlock_client, account_id, limit=5)
    hero_map = await safe_get_hero_map(deadlock_client)

    profile_lines = [f"{display_name}"]
    if mmr_rows:
        mmr = mmr_rows[0]
        player_score = mmr.get("player_score")
        rank_name = format_rank_name(mmr.get("division"), mmr.get("division_tier"))
        if rank_name:
            profile_lines.append(f"Rank: {rank_name}")
        else:
            profile_lines.append(
                f"MMR rank: {mmr.get('rank')} | division: {mmr.get('division')}.{mmr.get('division_tier')}"
            )
        if isinstance(player_score, (int, float)):
            profile_lines.append(f"Player score: {player_score:.2f}")
    else:
        profile_lines.append("MMR пока не найден в публичном API.")

    if hero_stats:
        total_matches = sum(int(row.get("matches_played", 0) or 0) for row in hero_stats)
        total_wins = sum(int(row.get("wins", 0) or 0) for row in hero_stats)
        top_hero = max(hero_stats, key=lambda row: int(row.get("matches_played", 0) or 0))
        top_hero_name = hero_name_for_id(hero_map, top_hero.get("hero_id"))
        winrate = (total_wins / total_matches * 100.0) if total_matches else 0.0
        profile_lines.append(f"Матчей: {total_matches} | Winrate: {format_percent(winrate)}")
        profile_lines.append(
            f"Топ герой: {top_hero_name} ({int(top_hero.get('matches_played', 0) or 0)} matches)"
        )
    else:
        profile_lines.append("Публичной статистики по героям пока нет.")

    if recent_matches:
        last_match = recent_matches[0]
        recent_wins = sum(1 for match in recent_matches if match.get("match_result") == 1)
        recent_winrate = recent_wins / len(recent_matches) * 100.0
        last_hero_name = hero_name_for_id(hero_map, last_match.get("hero_id"))
        last_duration = format_duration_compact(last_match.get("match_duration_s")) or "unknown"
        profile_lines.append(
            f"Последний матч: {format_result_icon(last_match.get('match_result'))} | "
            f"{last_hero_name} | "
            f"{last_match.get('player_kills', 0)}/{last_match.get('player_deaths', 0)}/{last_match.get('player_assists', 0)} | "
            f"{last_duration}"
        )
        profile_lines.append(
            f"Winrate за {len(recent_matches)} последних матчей: {format_percent(recent_winrate)}"
        )
    else:
        profile_lines.append("Недавние матчи в публичном API не найдены.")

    await update.message.reply_text("\n".join(profile_lines))


async def heroes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text("Использование: /heroes <steam vanity/link/id> [alltime|recent]")
        return

    mode = "alltime"
    if len(context.args) > 1:
        candidate_mode = context.args[-1].strip().lower()
        if candidate_mode in {"alltime", "recent"}:
            mode = candidate_mode
            context.args = context.args[:-1]

    _, display_name, account_id, _ = await resolve_player_context(update, context)
    if account_id is None or display_name is None:
        return

    deadlock_client = get_deadlock_client(context)
    hero_map = await safe_get_hero_map(deadlock_client)
    if mode == "recent":
        recent_matches = await safe_get_match_history(deadlock_client, account_id, limit=20)
        if not recent_matches:
            await update.message.reply_text(f"По {display_name} не удалось получить recent match-history.")
            return

        recent_summary = summarize_recent_heroes(recent_matches)
        top_rows = sorted(
            recent_summary.items(),
            key=lambda item: item[1]["matches"],
            reverse=True,
        )[:5]
        lines = [f"Топ герои recent: {display_name}"]
        for hero_id, stats in top_rows:
            matches = stats["matches"]
            wins = stats["wins"]
            winrate = (wins / matches * 100.0) if matches else 0.0
            hero_name = hero_name_for_id(hero_map, hero_id)
            lines.append(f"{hero_name}: {matches} matches, {format_percent(winrate)} WR")
        await update.message.reply_text("\n".join(lines))
        return

    hero_stats = await safe_get_player_hero_stats(deadlock_client, [account_id])
    if not hero_stats:
        await update.message.reply_text(f"По {display_name} пока нет публичной hero-статистики all-time.")
        return

    top_rows = sorted(
        hero_stats,
        key=lambda row: int(row.get("matches_played", 0) or 0),
        reverse=True,
    )[:5]

    lines = [f"Топ герои all-time: {display_name}"]
    for row in top_rows:
        matches = int(row.get("matches_played", 0) or 0)
        wins = int(row.get("wins", 0) or 0)
        winrate = (wins / matches * 100.0) if matches else 0.0
        hero_name = hero_name_for_id(hero_map, row.get("hero_id"))
        lines.append(f"{hero_name}: {matches} matches, {format_percent(winrate)} WR")

    await update.message.reply_text("\n".join(lines))


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text("Использование: /live <steam vanity/link/id>")
        return

    steam_client = get_steam_client(context)
    if not steam_client:
        await update.message.reply_text("Steam API клиент не инициализирован.")
        return

    steam_ref = context.args[0].strip()
    steam_id = await safe_resolve_user_reference(steam_client, steam_ref)
    if not steam_id:
        await update.message.reply_text(
            "Не удалось распознать игрока. Пришли vanity, vanity URL или ссылку Steam-профиля."
        )
        return

    player_summary_map = await safe_get_player_summaries(steam_client, [steam_id])
    player_summary = player_summary_map.get(steam_id)
    display_name = (
        normalize_public_user_reference(steam_ref)
        or (player_summary.get("personaname") if player_summary else None)
        or "игрок"
    )

    if not is_in_deadlock(player_summary):
        await update.message.reply_text(f"{display_name} сейчас не в Deadlock.")
        return

    account_id = steam_id64_to_account_id(steam_id)
    if account_id is None:
        await update.message.reply_text(f"{display_name} сейчас в Deadlock.")
        return

    deadlock_client = get_deadlock_client(context)
    active_matches = await safe_get_active_matches(deadlock_client, [account_id])
    if not active_matches:
        await update.message.reply_text(
            f"{display_name} сейчас в Deadlock, но публичный live-match у community API не найден."
        )
        return

    active_match = active_matches[0]
    player_entry = find_player_in_active_match(active_match, account_id)
    duration_text = format_duration_compact(active_match.get("duration_s"))
    mode = active_match.get("match_mode_parsed") or active_match.get("game_mode_parsed") or "Unknown"
    hero_id = player_entry.get("hero_id") if player_entry else None
    spectators = active_match.get("spectators")
    lines = [f"{display_name} сейчас в live-матче Deadlock."]
    if duration_text:
        lines.append(f"Длительность: {duration_text}")
    lines.append(f"Режим: {mode}")
    if active_match.get("match_id") is not None:
        lines.append(f"Match ID: {active_match['match_id']}")
    if hero_id is not None:
        lines.append(f"Hero ID: {hero_id}")
    if spectators is not None:
        lines.append(f"Зрителей: {spectators}")

    await update.message.reply_text("\n".join(lines))


async def friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    store = get_store(context)
    records = store.list_friends(update.effective_chat.id)
    if not records:
        await update.message.reply_text("Список отслеживаемых игроков пуст.")
        return

    lines = ["Отслеживаемые игроки:"]
    for record in records:
        if record.alias and record.public_id:
            lines.append(f"- {record.alias} ({record.public_id})")
            continue
        lines.append(f"- {record.display_name}")
    await update.message.reply_text("\n".join(lines))


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    if not monitoring_enabled(context):
        await update.message.reply_text("Мониторинг Steam выключен: не задан STEAM_API_KEY.")
        return

    store = get_store(context)
    records = store.list_friends(update.effective_chat.id)
    if not records:
        await update.message.reply_text("Список отслеживаемых игроков пуст.")
        return

    steam_client = get_steam_client(context)
    players = await safe_get_player_summaries(steam_client, [record.steam_id for record in records])
    if not players:
        await update.message.reply_text("Не удалось получить данные Steam API.")
        return

    for record in records:
        player = players.get(record.steam_id)
        player_name = player.get("personaname", record.last_player_name or record.steam_id) if player else (
            record.last_player_name or record.steam_id
        )
        store.update_status(update.effective_chat.id, record.steam_id, player_name, is_in_deadlock(player))

    refreshed_records = store.list_friends(update.effective_chat.id)
    active_lines = [
        format_friend_status(record, players.get(record.steam_id))
        for record in refreshed_records
        if is_in_deadlock(players.get(record.steam_id))
    ]
    if not active_lines:
        await update.message.reply_text("Сейчас никто из списка не в Deadlock.")
        return

    await update.message.reply_text("\n".join(active_lines))


async def monitor_loop(application: Application) -> None:
    config: BotConfig = application.bot_data["config"]
    store: FriendRepository = application.bot_data["friend_store"]
    steam_client: Optional[SteamApiClient] = application.bot_data.get("steam_client")

    if not steam_client:
        return

    while True:
        records = store.get_all_friends()
        if records:
            steam_ids = sorted({record.steam_id for record in records})
            players = await safe_get_player_summaries(steam_client, steam_ids)

            if players:
                for record in records:
                    player = players.get(record.steam_id)
                    player_name = (
                        player.get("personaname", record.last_player_name or record.steam_id)
                        if player
                        else record.last_player_name or record.steam_id
                    )
                    in_deadlock = is_in_deadlock(player)
                    if record.last_in_deadlock != in_deadlock:
                        await application.bot.send_message(
                            chat_id=record.chat_id,
                            text=format_transition_message(record, player),
                        )
                    store.update_status(record.chat_id, record.steam_id, player_name, in_deadlock)

        await asyncio.sleep(config.poll_interval_seconds)


async def on_startup(application: Application) -> None:
    config: BotConfig = application.bot_data["config"]
    if config.steam_api_key:
        application.bot_data["monitor_task"] = application.create_task(monitor_loop(application))


async def on_shutdown(application: Application) -> None:
    monitor_task: Optional[asyncio.Task] = application.bot_data.get("monitor_task")
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled bot error", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("Команда временно упала с ошибкой. Попробуй еще раз.")
        except Exception:
            LOGGER.exception("Failed to send error message")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Не найден TELEGRAM_BOT_TOKEN. Скопируй .env.example в .env и укажи токен."
        )
    steam_api_key = os.getenv("STEAM_API_KEY")
    poll_interval_seconds = int(os.getenv("STEAM_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL))
    storage_backend = os.getenv("STORAGE_BACKEND", "sqlite")
    database_path = os.getenv("DATABASE_PATH", "deadbot.sqlite3")

    config = BotConfig(
        steam_api_key=steam_api_key,
        poll_interval_seconds=max(15, poll_interval_seconds),
    )
    store = create_friend_repository(storage_backend, database_path)

    application = (
        Application.builder()
        .token(token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    application.bot_data["config"] = config
    application.bot_data["friend_store"] = store
    application.bot_data["deadlock_client"] = DeadlockApiClient()
    if steam_api_key:
        application.bot_data["steam_client"] = SteamApiClient(steam_api_key)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("hero", hero))
    application.add_handler(CommandHandler("tip", tip))
    application.add_handler(CommandHandler("addfriend", addfriend))
    application.add_handler(CommandHandler("importfriends", importfriends))
    application.add_handler(CommandHandler("removefriend", removefriend))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("heroes", heroes))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("friends", friends))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("helpme", helpme))
    application.add_error_handler(on_error)
    application.run_polling()


if __name__ == "__main__":
    main()
