"""
cache.py — Cache disque simple
Évite de re-scraper la même chaîne à chaque run.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


CACHE_DIR = Path(__file__).parent.parent / "exports" / ".cache"


def _cache_key(url: str) -> str:
    """Génère une clé de cache depuis une URL."""
    return hashlib.md5(url.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get_cached(url: str, max_age_hours: int = 24) -> dict | None:
    """
    Récupère une entrée en cache si elle existe et n'est pas expirée.
    Retourne None si le cache est invalide ou expiré.
    """
    key = _cache_key(url)
    path = _cache_path(key)

    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        entry = json.load(f)

    cached_at = datetime.fromisoformat(entry["cached_at"])
    if datetime.now().astimezone() - cached_at > timedelta(hours=max_age_hours):
        return None

    return entry["data"]


def set_cached(url: str, data: dict):
    """Stocke une entrée en cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(url)
    path = _cache_path(key)

    entry = {
        "url": url,
        "cached_at": datetime.now().astimezone().isoformat(),
        "data": data,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)


def clear_cache():
    """Vide tout le cache."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()


def get_cache_info() -> list[dict]:
    """Retourne les infos sur les entrées en cache."""
    if not CACHE_DIR.exists():
        return []
    entries = []
    for f in CACHE_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fh:
            entry = json.load(fh)
        entries.append({
            "url": entry["url"],
            "cached_at": entry["cached_at"],
            "size_kb": f.stat().st_size / 1024,
        })
    return entries
