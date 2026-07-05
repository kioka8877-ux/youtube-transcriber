"""
F01_RECON — Frégate de reconnaissance
Liste les vidéos d'une chaîne YouTube ou d'une vidéo unique via yt-dlp.
"""

import subprocess
import re


def is_channel_url(url: str) -> bool:
    """Détecte si l'URL est une chaîne ou une playlist."""
    patterns = [
        r"youtube\.com/@[\w-]+",
        r"youtube\.com/channel/[\w-]+",
        r"youtube\.com/c/[\w-]+",
        r"youtube\.com/user/[\w-]+",
        r"youtube\.com/playlist\?list=",
    ]
    return any(re.search(p, url) for p in patterns)


def is_video_url(url: str) -> bool:
    """Détecte si l'URL est une vidéo YouTube unique."""
    return bool(re.search(r"(youtube\.com/watch\?v=|youtu\.be/)", url))


def list_channel_videos(channel_url: str) -> list[dict]:
    """
    Liste toutes les vidéos d'une chaîne via yt-dlp --flat-playlist.
    Retourne une liste de dicts: {video_id, title, url, duration}.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(url)s\t%(duration)s",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            videos.append({
                "video_id": parts[0],
                "title": parts[1],
                "url": parts[2],
                "duration": float(parts[3]) if len(parts) > 3 and parts[3] != "NA" else None,
            })

    return videos


def get_single_video(video_url: str) -> dict:
    """
    Récupère les métadonnées d'une vidéo unique via yt-dlp.
    """
    cmd = [
        "yt-dlp",
        "--print", "%(id)s\t%(title)s\t%(url)s\t%(duration)s",
        "--no-warnings",
        video_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    parts = result.stdout.strip().split("\t")
    if len(parts) >= 3:
        return {
            "video_id": parts[0],
            "title": parts[1],
            "url": parts[2],
            "duration": float(parts[3]) if len(parts) > 3 and parts[3] != "NA" else None,
        }
    return {}


def run(url: str) -> dict:
    """
    Point d'entrée de la frégate RECON.
    Retourne {videos: [...], meta: {...}}.
    """
    if is_video_url(url):
        video = get_single_video(url)
        videos = [video] if video else []
    elif is_channel_url(url):
        videos = list_channel_videos(url)
    else:
        raise ValueError(f"URL non reconnue: {url}")

    total_duration = sum(v["duration"] or 0 for v in videos)

    return {
        "videos": videos,
        "meta": {
            "source_url": url,
            "video_count": len(videos),
            "duree_totale_sec": total_duration,
        }
    }
