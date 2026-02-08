"""Cache management for ClawHub skill data."""
from __future__ import annotations

import time

from .utils import DATA_DIR, load_json, save_json

CACHE_FILE = DATA_DIR / "clawhub-cache.json"
CACHE_MAX_AGE = 86400  # 24 hours in seconds


def is_cache_fresh(cache_data: dict) -> bool:
    """Check if cache is less than 24 hours old."""
    if not cache_data or "timestamp" not in cache_data:
        return False
    cache_age = time.time() - cache_data["timestamp"]
    return cache_age < CACHE_MAX_AGE


def load_cache() -> dict:
    """Load local cache file."""
    try:
        if CACHE_FILE.exists():
            data = load_json(CACHE_FILE)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def save_cache(data: dict) -> dict:
    """Save cache file with timestamp. Returns updated data."""
    data["timestamp"] = time.time()
    save_json(CACHE_FILE, data)
    return data


def search_cache(cache_data: dict, query: str, limit: int) -> list[dict]:
    """Search cached skills by keyword matching.

    Args:
        cache_data: Loaded cache dict
        query: Search query
        limit: Maximum results

    Returns:
        Matching skill data dicts from cache
    """
    if "skills" not in cache_data:
        return []

    query_lower = query.lower()
    matches = []

    for skill_data in cache_data["skills"]:
        name = skill_data.get("name", "").lower()
        desc = skill_data.get("description", "").lower()
        tags = [t.lower() for t in skill_data.get("tags", [])]

        if (query_lower in name or
            query_lower in desc or
            any(query_lower in tag for tag in tags)):
            matches.append(skill_data)

    return matches[:limit]
