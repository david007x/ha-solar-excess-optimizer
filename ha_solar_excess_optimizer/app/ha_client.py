import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

HA_URL   = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


def _headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


async def get_state(entity_id: str) -> dict | None:
    try:
        session = _get_session()
        async with session.get(f"{HA_URL}/api/states/{entity_id}", headers=_headers()) as r:
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
        session = _get_session()
        async with session.post(url, headers=_headers(),
                                json={"entity_id": entity_id, "value": value}) as r:
            if r.status not in (200, 201):
                logger.warning(f"set_number({entity_id}, {value}): HTTP {r.status}")
    except Exception as e:
        logger.error(f"set_number({entity_id}, {value}): {e}")


async def get_all_states() -> list[dict]:
    """Fetch all entity states from HA."""
    try:
        session = _get_session()
        async with session.get(f"{HA_URL}/api/states", headers=_headers()) as r:
            return await r.json() if r.status == 200 else []
    except Exception as e:
        logger.error(f"get_all_states: {e}")
        return []


async def _call_service(domain: str, service: str, entity_id: str):
    url = f"{HA_URL}/api/services/{domain}/{service}"
    try:
        session = _get_session()
        async with session.post(url, headers=_headers(), json={"entity_id": entity_id}) as r:
            if r.status not in (200, 201):
                logger.warning(f"service {domain}.{service}({entity_id}): HTTP {r.status}")
    except Exception as e:
        logger.error(f"service {domain}.{service}({entity_id}): {e}")
