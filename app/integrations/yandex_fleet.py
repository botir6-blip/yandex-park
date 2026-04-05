import os
import requests

BASE_URL = "https://fleet-api.taxi.yandex.net"

def headers():
    return {
        "X-Client-ID": os.getenv("YANDEX_CLIENT_ID", ""),
        "X-API-Key": os.getenv("YANDEX_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept-Language": "ru",
    }

def find_driver(text: str):
    payload = {
        "query": {
            "park": {"id": os.getenv("YANDEX_PARK_ID", "")},
            "text": text
        },
        "fields": {
            "driver_profile": ["id", "first_name", "last_name"],
            "account": ["id", "balance", "currency"]
        },
        "limit": 10,
        "offset": 0
    }
    r = requests.post(
        f"{BASE_URL}/v1/parks/driver-profiles/list",
        headers=headers(),
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()
