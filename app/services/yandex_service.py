from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.models import Driver
from app.utils import normalize_phone

BASE_URL = "https://fleet-api.taxi.yandex.net"


class YandexFleetError(Exception):
    pass


@dataclass
class YandexBalanceResult:
    ok: bool
    profile_id: str | None = None
    balance: str | None = None
    currency: str | None = None
    note: str | None = None


def is_enabled() -> bool:
    return bool(settings.yandex_park_id and settings.yandex_client_id and settings.yandex_api_key)


def _headers() -> dict[str, str]:
    return {
        "X-Client-ID": settings.yandex_client_id,
        "X-API-Key": settings.yandex_api_key,
        "Content-Type": "application/json",
        "Accept-Language": "ru",
    }


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(f"{BASE_URL}{path}", data=body, headers=_headers(), method="POST")
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise YandexFleetError(f"Yandex API HTTP {exc.code}: {detail[:300]}") from exc
    except URLError as exc:
        raise YandexFleetError(f"Yandex API unavailable: {exc.reason}") from exc


def _driver_fields() -> dict[str, list[str]]:
    return {
        "driver_profile": ["id", "first_name", "last_name", "phones"],
        "account": ["id", "balance", "currency"],
        "car": [],
        "park": [],
    }


def find_profiles_by_phone(phone: str) -> list[dict[str, Any]]:
    normalized = normalize_phone(phone)
    if not normalized:
        return []

    tried: list[str] = []
    for query_text in [normalized, normalized.replace('+', '')]:
        if not query_text or query_text in tried:
            continue
        tried.append(query_text)
        payload = {
            "query": {
                "park": {"id": settings.yandex_park_id},
                "text": query_text,
            },
            "fields": _driver_fields(),
            "limit": 20,
            "offset": 0,
        }
        data = _post("/v1/parks/driver-profiles/list", payload)
        rows = data.get("driver_profiles") or []
        if rows:
            return rows
    return []


def choose_profile_for_phone(phone: str, profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_phone(phone)
    if not profiles:
        return None

    exact_matches: list[dict[str, Any]] = []
    for item in profiles:
        phone_list = (item.get("driver_profile") or {}).get("phones") or []
        if normalized and normalized in phone_list:
            exact_matches.append(item)

    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(profiles) == 1:
        return profiles[0]
    return exact_matches[0] if exact_matches else None


def auto_link_driver_by_phone(driver: Driver) -> str | None:
    if not is_enabled() or driver.yandex_contractor_profile_id:
        return driver.yandex_contractor_profile_id

    profiles = find_profiles_by_phone(driver.phone)
    chosen = choose_profile_for_phone(driver.phone, profiles)
    if not chosen:
        return None

    profile_id = (chosen.get("driver_profile") or {}).get("id")
    if profile_id:
        driver.yandex_contractor_profile_id = profile_id
    return profile_id


def fetch_balance_by_profile_id(profile_id: str) -> YandexBalanceResult:
    payload = {
        "query": {
            "park": {
                "id": settings.yandex_park_id,
                "driver_profile": {"id": [profile_id]},
            }
        },
        "fields": _driver_fields(),
        "limit": 1,
        "offset": 0,
    }
    data = _post("/v1/parks/driver-profiles/list", payload)
    rows = data.get("driver_profiles") or []
    if not rows:
        return YandexBalanceResult(ok=False, profile_id=profile_id, note="Профиль не найден в Яндексе.")

    item = rows[0]
    account = ((item.get("accounts") or [{}])[0])
    return YandexBalanceResult(
        ok=True,
        profile_id=(item.get("driver_profile") or {}).get("id") or profile_id,
        balance=account.get("balance"),
        currency=account.get("currency"),
        note=None,
    )


def get_driver_balance(driver: Driver, *, auto_link: bool = True) -> YandexBalanceResult:
    if not is_enabled():
        return YandexBalanceResult(ok=False, note="Яндекс интеграцияси ҳали ёқилмаган.")

    profile_id = driver.yandex_contractor_profile_id
    if not profile_id and auto_link:
        profile_id = auto_link_driver_by_phone(driver)

    if not profile_id:
        return YandexBalanceResult(ok=False, note="Яндекс профили телефон бўйича топилмади.")

    result = fetch_balance_by_profile_id(profile_id)
    if result.ok and result.profile_id and driver.yandex_contractor_profile_id != result.profile_id:
        driver.yandex_contractor_profile_id = result.profile_id
    return result
