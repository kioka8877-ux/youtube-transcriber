"""
F01_RECON — Frégate de reconnaissance
Liste les vidéos d'une chaîne YouTube ou d'une vidéo unique via YouTube Data API v3.
Fallback: yt-dlp si l'API n'est pas configurée.
"""

import os
import re
import requests


YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
API_BASE = "https://www.googleapis.com/youtube/v3"


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


def _extract_video_id(url: str) -> str | None:
    """Extrait le video_id d'une URL YouTube."""
    m = re.search(r"[?&]v=([\w-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([\w-]{11})", url)
    if m:
        return m.group(1)
    return None


def _resolve_channel_id(url: str) -> str | None:
    """
    Résout une URL de chaîne en channel ID via l'API.
    Gère les formats @handle, /channel/, /c/, /user/.
    """
    # /channel/UCxxxx
    m = re.search(r"youtube\.com/channel/([\w-]+)", url)
    if m:
        return m.group(1)

    # @handle
    m = re.search(r"youtube\.com/@([\w-]+)", url)
    if m:
        handle = m.group(1)
        r = requests.get(f"{API_BASE}/channels", params={
            "part": "id",
            "forHandle": handle,
            "key": YOUTUBE_API_KEY,
        }, timeout=30)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["id"]

    # /c/Name ou /user/Name
    m = re.search(r"youtube\.com/(?:c|user)/([\w-]+)", url)
    if m:
        name = m.group(1)
        # Search pour trouver la chaîne
        r = requests.get(f"{API_BASE}/search", params={
            "part": "snippet",
            "type": "channel",
            "q": name,
            "key": YOUTUBE_API_KEY,
            "maxResults": 1,
        }, timeout=30)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["id"]["channelId"]

    return None


def _get_video_details(video_id: str) -> dict:
    """Récupère les détails d'une vidéo unique via l'API."""
    r = requests.get(f"{API_BASE}/videos", params={
        "part": "snippet,contentDetails",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }, timeout=30)

    if r.status_code != 200:
        return {}

    items = r.json().get("items", [])
    if not items:
        return {}

    item = items[0]
    duration_str = item.get("contentDetails", {}).get("duration", "PT0S")
    duration = _parse_iso8601_duration(duration_str)

    return {
        "video_id": video_id,
        "title": item["snippet"]["title"],
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "duration": duration,
        "published": item["snippet"]["publishedAt"],
    }


def _parse_iso8601_duration(duration: str) -> float:
    """Parse une durée ISO 8601 (PT1H2M3S) en secondes."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not m:
        return 0.0
    h = int(m.group(1) or 0)
    m_val = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + m_val * 60 + s


def list_channel_videos_api(channel_url: str) -> list[dict]:
    """
    Liste toutes les vidéos d'une chaîne via YouTube Data API v3.
    Utilise l'uploads playlist + pagination.
    """
    channel_id = _resolve_channel_id(channel_url)
    if not channel_id:
        raise ValueError(f"Impossible de résoudre l'ID de chaîne: {channel_url}")

    # Récupérer l'uploads playlist ID
    r = requests.get(f"{API_BASE}/channels", params={
        "part": "contentDetails,snippet",
        "id": channel_id,
        "key": YOUTUBE_API_KEY,
    }, timeout=30)

    if r.status_code != 200:
        raise RuntimeError(f"API channels.list error: {r.status_code} {r.text[:200]}")

    items = r.json().get("items", [])
    if not items:
        raise ValueError(f"Chaîne non trouvée: {channel_id}")

    channel_info = items[0]
    channel_name = channel_info["snippet"]["title"]
    uploads_playlist = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

    # Paginer through playlistItems
    all_videos = []
    page_token = None

    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist,
            "key": YOUTUBE_API_KEY,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        r = requests.get(f"{API_BASE}/playlistItems", params=params, timeout=30)
        if r.status_code != 200:
            print(f"   ⚠️ playlistItems error: {r.status_code} {r.text[:200]}")
            break

        data = r.json()
        for item in data.get("items", []):
            all_videos.append({
                "video_id": item["contentDetails"]["videoId"],
                "title": item["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                "duration": None,  # pas dispo dans playlistItems
                "published": item["contentDetails"].get("videoPublishedAt", ""),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    # Batch: récupérer les durées via videos.list (50 à la fois)
    for i in range(0, len(all_videos), 50):
        batch = all_videos[i:i + 50]
        ids = ",".join(v["video_id"] for v in batch)
        r = requests.get(f"{API_BASE}/videos", params={
            "part": "contentDetails",
            "id": ids,
            "key": YOUTUBE_API_KEY,
        }, timeout=30)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                vid_id = item["id"]
                dur = _parse_iso8601_duration(item.get("contentDetails", {}).get("duration", "PT0S"))
                for v in all_videos:
                    if v["video_id"] == vid_id:
                        v["duration"] = dur
                        break

    return all_videos


def list_channel_videos_ytdlp(channel_url: str) -> list[dict]:
    """Fallback: yt-dlp si l'API n'est pas configurée."""
    import subprocess
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
                "published": "",
            })
    return videos


def get_single_video(video_url: str) -> dict:
    """Récupère les métadonnées d'une vidéo unique."""
    vid_id = _extract_video_id(video_url)
    if not vid_id:
        return {}

    if YOUTUBE_API_KEY:
        return _get_video_details(vid_id)

    # Fallback sans API
    return {
        "video_id": vid_id,
        "title": f"Video {vid_id}",
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "duration": None,
        "published": "",
    }


def run(url: str) -> dict:
    """
    Point d'entrée de la frégate RECON.
    Retourne {videos: [...], meta: {...}}.
    """
    if YOUTUBE_API_KEY:
        print("   📡 Mode: YouTube Data API v3")
    else:
        print("   ⚠️ Mode: yt-dlp (pas de clé API)")

    if is_video_url(url):
        video = get_single_video(url)
        videos = [video] if video else []
    elif is_channel_url(url):
        if YOUTUBE_API_KEY:
            videos = list_channel_videos_api(url)
        else:
            videos = list_channel_videos_ytdlp(url)
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
