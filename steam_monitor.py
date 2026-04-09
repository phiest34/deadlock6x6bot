import asyncio
import json
import time
from typing import Iterable, Optional
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import re

from storage import FriendRecord


DEADLOCK_APP_ID = "1422450"
STEAM_ID64_BASE = 76561197960265728
VANITY_URL_RE = re.compile(r"steamcommunity\.com/id/([^/?#]+)/?", re.IGNORECASE)
PROFILE_URL_RE = re.compile(r"steamcommunity\.com/profiles/(\d{17})/?", re.IGNORECASE)

class SteamApiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def get_player_summaries(self, steam_ids: Iterable[str]) -> dict[str, dict]:
        ids = [steam_id for steam_id in steam_ids if steam_id]
        if not ids:
            return {}
        return await asyncio.to_thread(self._fetch_player_summaries, ids)

    async def get_friend_list(self, steam_id: str) -> list[str]:
        return await asyncio.to_thread(self._fetch_friend_list, steam_id)

    async def resolve_user_reference(self, value: str) -> Optional[str]:
        normalized = normalize_user_reference(value)
        if not normalized:
            return None
        if is_valid_steam_id(normalized):
            return normalized
        return await asyncio.to_thread(self._resolve_vanity_url, normalized)

    def _fetch_player_summaries(self, steam_ids: list[str]) -> dict[str, dict]:
        query = urlencode(
            {
                "key": self.api_key,
                "steamids": ",".join(steam_ids),
            }
        )
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?{query}"
        with urlopen(url, timeout=15) as response:
            payload = json.load(response)

        players = payload.get("response", {}).get("players", [])
        return {str(player["steamid"]): player for player in players}

    def _resolve_vanity_url(self, vanity_value: str) -> Optional[str]:
        query = urlencode(
            {
                "key": self.api_key,
                "vanityurl": vanity_value,
            }
        )
        url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?{query}"
        with urlopen(url, timeout=15) as response:
            payload = json.load(response)

        response_data = payload.get("response", {})
        if response_data.get("success") != 1:
            return None
        steam_id = str(response_data.get("steamid", "")).strip()
        if not is_valid_steam_id(steam_id):
            return None
        return steam_id

    def _fetch_friend_list(self, steam_id: str) -> list[str]:
        query = urlencode(
            {
                "key": self.api_key,
                "steamid": steam_id,
                "relationship": "friend",
            }
        )
        url = f"https://api.steampowered.com/ISteamUser/GetFriendList/v0001/?{query}"
        with urlopen(url, timeout=15) as response:
            payload = json.load(response)

        friends = payload.get("friendslist", {}).get("friends", [])
        return [
            str(friend.get("steamid", "")).strip()
            for friend in friends
            if is_valid_steam_id(str(friend.get("steamid", "")).strip())
        ]


class DeadlockApiClient:
    def __init__(self, base_url: str = "https://api.deadlock-api.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.assets_base_url = "https://assets.deadlock-api.com"
        self._hero_map_cache: Optional[dict[int, str]] = None

    async def get_active_matches(self, account_ids: list[int]) -> list[dict]:
        return await asyncio.to_thread(self._fetch_active_matches, account_ids)

    async def get_player_mmr(self, account_ids: list[int]) -> list[dict]:
        return await asyncio.to_thread(self._fetch_player_mmr, account_ids)

    async def get_player_hero_stats(self, account_ids: list[int]) -> list[dict]:
        return await asyncio.to_thread(self._fetch_player_hero_stats, account_ids)

    async def get_match_history(self, account_id: int, limit: int = 5) -> list[dict]:
        return await asyncio.to_thread(self._fetch_match_history, account_id, limit)

    async def get_hero_map(self) -> dict[int, str]:
        if self._hero_map_cache is not None:
            return self._hero_map_cache
        return await asyncio.to_thread(self._fetch_hero_map)

    def _fetch_active_matches(self, account_ids: list[int]) -> list[dict]:
        if not account_ids:
            return []

        query = urlencode(
            {
                "account_ids": ",".join(str(account_id) for account_id in account_ids),
            }
        )
        url = f"{self.base_url}/v1/matches/active?{query}"
        with urlopen(self._build_request(url), timeout=15) as response:
            payload = json.load(response)

        if not isinstance(payload, list):
            return []
        return payload

    def _fetch_player_mmr(self, account_ids: list[int]) -> list[dict]:
        if not account_ids:
            return []

        query = urlencode(
            {
                "account_ids": ",".join(str(account_id) for account_id in account_ids),
            }
        )
        url = f"{self.base_url}/v1/players/mmr?{query}"
        with urlopen(self._build_request(url), timeout=15) as response:
            payload = json.load(response)

        if not isinstance(payload, list):
            return []
        return payload

    def _fetch_player_hero_stats(self, account_ids: list[int]) -> list[dict]:
        if not account_ids:
            return []

        query = urlencode(
            {
                "account_ids": ",".join(str(account_id) for account_id in account_ids),
            }
        )
        url = f"{self.base_url}/v1/players/hero-stats?{query}"
        with urlopen(self._build_request(url), timeout=15) as response:
            payload = json.load(response)

        if not isinstance(payload, list):
            return []
        return payload

    def _fetch_match_history(self, account_id: int, limit: int) -> list[dict]:
        query = urlencode({"limit": limit})
        url = f"{self.base_url}/v1/players/{account_id}/match-history?{query}"
        with urlopen(self._build_request(url), timeout=15) as response:
            payload = json.load(response)

        if not isinstance(payload, list):
            return []
        return payload

    def _fetch_hero_map(self) -> dict[int, str]:
        url = f"{self.assets_base_url}/v2/heroes"
        with urlopen(self._build_request(url), timeout=15) as response:
            payload = json.load(response)

        hero_map: dict[int, str] = {}
        if isinstance(payload, list):
            for hero in payload:
                hero_id = hero.get("id")
                name = hero.get("name")
                if isinstance(hero_id, int) and isinstance(name, str):
                    hero_map[hero_id] = name
        self._hero_map_cache = hero_map
        return hero_map

    @staticmethod
    def _build_request(url: str) -> Request:
        return Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
            },
        )


def normalize_user_reference(value: str) -> Optional[str]:
    candidate = value.strip()
    if not candidate:
        return None

    profile_match = PROFILE_URL_RE.search(candidate)
    if profile_match:
        return profile_match.group(1)

    vanity_match = VANITY_URL_RE.search(candidate)
    if vanity_match:
        return vanity_match.group(1)

    if is_valid_steam_id(candidate):
        return candidate

    if "/" not in candidate and " " not in candidate:
        return candidate

    return None


def normalize_public_user_reference(value: str) -> Optional[str]:
    candidate = value.strip()
    if not candidate:
        return None

    profile_match = PROFILE_URL_RE.search(candidate)
    if profile_match:
        return candidate

    vanity_match = VANITY_URL_RE.search(candidate)
    if vanity_match:
        return vanity_match.group(1)

    if is_valid_steam_id(candidate):
        return None

    if "/" not in candidate and " " not in candidate:
        return candidate

    return None


def public_id_from_player(player: Optional[dict]) -> Optional[str]:
    if not player:
        return None

    profile_url = str(player.get("profileurl", "")).strip()
    if not profile_url:
        return None

    vanity_match = VANITY_URL_RE.search(profile_url)
    if vanity_match:
        return vanity_match.group(1)

    profile_match = PROFILE_URL_RE.search(profile_url)
    if profile_match:
        parsed = urlparse(profile_url)
        return f"{parsed.scheme}://{parsed.netloc}/profiles/{profile_match.group(1)}"

    return profile_url


def is_valid_steam_id(value: str) -> bool:
    return value.isdigit() and len(value) == 17


def steam_id64_to_account_id(steam_id: str) -> Optional[int]:
    if not is_valid_steam_id(steam_id):
        return None
    account_id = int(steam_id) - STEAM_ID64_BASE
    if account_id < 0:
        return None
    return account_id


def is_in_deadlock(player: Optional[dict]) -> bool:
    if not player:
        return False
    return str(player.get("gameid", "")) == DEADLOCK_APP_ID


def format_friend_status(record: FriendRecord, player: Optional[dict]) -> str:
    player_name = None
    if player:
        player_name = player.get("personaname")

    display_name = record.alias or player_name or record.last_player_name or record.public_id or "unknown"
    if is_in_deadlock(player):
        minutes = minutes_in_deadlock(record.entered_deadlock_at)
        if minutes is not None:
            return f"{display_name} сейчас в Deadlock уже {minutes} мин."
        return f"{display_name} сейчас в Deadlock."
    return f"{display_name} сейчас не в Deadlock."


def format_transition_message(record: FriendRecord, player: Optional[dict]) -> str:
    player_name = None
    if player:
        player_name = player.get("personaname")

    display_name = record.alias or player_name or record.last_player_name or record.public_id or "unknown"
    if is_in_deadlock(player):
        return f"{display_name} зашел в Deadlock."
    return f"{display_name} вышел из Deadlock."


def minutes_in_deadlock(entered_deadlock_at: Optional[int]) -> Optional[int]:
    if not entered_deadlock_at:
        return None
    elapsed_seconds = max(0, int(time.time()) - int(entered_deadlock_at))
    return elapsed_seconds // 60


async def safe_get_player_summaries(client: SteamApiClient, steam_ids: list[str]) -> dict[str, dict]:
    try:
        return await client.get_player_summaries(steam_ids)
    except TimeoutError:
        return {}
    except URLError:
        return {}
    except OSError:
        return {}


async def safe_resolve_user_reference(client: SteamApiClient, value: str) -> Optional[str]:
    try:
        return await client.resolve_user_reference(value)
    except TimeoutError:
        return None
    except URLError:
        return None
    except OSError:
        return None


async def safe_get_friend_list(client: SteamApiClient, steam_id: str) -> list[str]:
    try:
        return await client.get_friend_list(steam_id)
    except TimeoutError:
        return []
    except URLError:
        return []
    except OSError:
        return []


async def safe_get_active_matches(client: DeadlockApiClient, account_ids: list[int]) -> list[dict]:
    try:
        return await client.get_active_matches(account_ids)
    except TimeoutError:
        return []
    except URLError:
        return []
    except OSError:
        return []


async def safe_get_player_mmr(client: DeadlockApiClient, account_ids: list[int]) -> list[dict]:
    try:
        return await client.get_player_mmr(account_ids)
    except TimeoutError:
        return []
    except URLError:
        return []
    except OSError:
        return []


async def safe_get_player_hero_stats(client: DeadlockApiClient, account_ids: list[int]) -> list[dict]:
    try:
        return await client.get_player_hero_stats(account_ids)
    except TimeoutError:
        return []
    except URLError:
        return []
    except OSError:
        return []


async def safe_get_match_history(client: DeadlockApiClient, account_id: int, limit: int = 5) -> list[dict]:
    try:
        return await client.get_match_history(account_id, limit)
    except TimeoutError:
        return []
    except URLError:
        return []
    except OSError:
        return []


async def safe_get_hero_map(client: DeadlockApiClient) -> dict[int, str]:
    try:
        return await client.get_hero_map()
    except TimeoutError:
        return {}
    except URLError:
        return {}
    except OSError:
        return {}
