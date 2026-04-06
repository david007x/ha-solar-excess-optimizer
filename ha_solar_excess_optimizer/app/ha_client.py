import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

HA_URL   = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def _headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


async def get_state(entity_id: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{HA_URL}/api/states/{entity_id}", headers=_headers()) as r:
                return await r.json() if r.status == 200 else None
    except Exception as e:
        logger.error(f"get_state({entity_id}): {e}")
        return None


async def get_numeric_state(entity_id: str) -> float:
    state = await get_state(entity_id)
    try:
        if not state:
            return 0.0
        raw = str(state["state"]).strip()
        # Europäisches Komma als Dezimaltrennzeichen behandeln (z.B. "1,2" → "1.2")
        raw = raw.replace(",", ".")
        return float(raw)
    except (ValueError, KeyError):
        return 0.0


async def is_on(entity_id: str) -> bool:
    state = await get_state(entity_id)
    return state is not None and state.get("state") == "on"


async def turn_on(entity_id: str):
    await _call_service("homeassistant", "turn_on", entity_id)


async def turn_off(entity_id: str):
    await _call_service("homeassistant", "turn_off", entity_id)


async def set_number(entity_id: str, value: float):
    """Set a number.* entity (e.g. wallbox ampere)."""
    url = f"{HA_URL}/api/services/number/set_value"
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(url, headers=_headers(),
                         json={"entity_id": entity_id, "value": value})
    except Exception as e:
        logger.error(f"set_number({entity_id}, {value}): {e}")


async def _call_service(domain: str, service: str, entity_id: str):
    url = f"{HA_URL}/api/services/{domain}/{service}"
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(url, headers=_headers(), json={"entity_id": entity_id})
    except Exception as e:
        logger.error(f"service {domain}.{service}({entity_id}): {e}")
