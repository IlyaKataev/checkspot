import aiohttp

from app.core.config import settings


async def geocode_address(address: str, city: str = "") -> dict | None:
    """
    Геокодирование через 2GIS (точнее для РФ).
    Если ключ не задан — fallback на Nominatim.
    """
    query = f"{city}, {address}" if city else address

    if settings.TWOGIS_API_KEY:
        result = await _geocode_2gis(query)
        if result:
            return result

    return await _geocode_nominatim(query)


async def _geocode_2gis(query: str) -> dict | None:
    url = "https://catalog.api.2gis.com/3.0/items/geocode"
    params = {
        "q": query,
        "fields": "items.point",
        "key": settings.TWOGIS_API_KEY,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                items = data.get("result", {}).get("items", [])
                if items and "point" in items[0]:
                    point = items[0]["point"]
                    return {"lat": float(point["lat"]), "lng": float(point["lon"])}
    except Exception:
        pass
    return None


async def _geocode_nominatim(query: str) -> dict | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "ru"}
    headers = {"User-Agent": "CheckSpot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                if data:
                    return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
    except Exception:
        pass
    return None
