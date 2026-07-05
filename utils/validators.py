"""
validators.py — Validation d'URLs YouTube/TikTok
"""

import re


def validate_youtube_url(url: str) -> bool:
    """Valide une URL YouTube (vidéo, chaîne, ou playlist)."""
    patterns = [
        r"youtube\.com/watch\?v=[\w-]+",
        r"youtu\.be/[\w-]+",
        r"youtube\.com/@[\w-]+",
        r"youtube\.com/channel/[\w-]+",
        r"youtube\.com/c/[\w-]+",
        r"youtube\.com/user/[\w-]+",
        r"youtube\.com/playlist\?list=[\w-]+",
    ]
    return any(re.search(p, url) for p in patterns)


def validate_tiktok_url(url: str) -> bool:
    """Valide une URL TikTok (vidéo ou profil)."""
    patterns = [
        r"tiktok\.com/@[\w.-]+/video/\d+",
        r"tiktok\.com/@[\w.-]+",
    ]
    return any(re.search(p, url) for p in patterns)


def detect_url_type(url: str) -> str:
    """
    Détecte le type d'URL.
    Retourne: 'youtube_video', 'youtube_channel', 'youtube_playlist',
              'tiktok_video', 'tiktok_profile', ou 'unknown'.
    """
    if re.search(r"(youtube\.com/watch\?v=|youtu\.be/)", url):
        return "youtube_video"
    if re.search(r"youtube\.com/playlist\?list=", url):
        return "youtube_playlist"
    if re.search(r"youtube\.com/(@[\w-]+|channel/[\w-]+|c/[\w-]+|user/[\w-]+)", url):
        return "youtube_channel"
    if re.search(r"tiktok\.com/@[\w.-]+/video/\d+", url):
        return "tiktok_video"
    if re.search(r"tiktok\.com/@[\w.-]+", url):
        return "tiktok_profile"
    return "unknown"


def validate_url(url: str) -> dict:
    """
    Validation complète d'une URL.
    Retourne {valid, platform, type, error}.
    """
    if not url or not url.strip():
        return {"valid": False, "platform": None, "type": None, "error": "URL vide"}

    url = url.strip()

    if validate_youtube_url(url):
        return {
            "valid": True,
            "platform": "youtube",
            "type": detect_url_type(url),
            "error": None,
        }

    if validate_tiktok_url(url):
        return {
            "valid": True,
            "platform": "tiktok",
            "type": detect_url_type(url),
            "error": None,
        }

    return {
        "valid": False,
        "platform": None,
        "type": "unknown",
        "error": f"URL non reconnue: {url}",
    }
