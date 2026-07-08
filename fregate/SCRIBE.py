"""
F02_SCRIBE — Frégate de transcription
Extrait les transcriptions avec timestamps via youtube-transcript-api.
Fallback: API timedtext de YouTube directement si la lib échoue.
Retry automatique sur HTTP 429 (rate-limit) avec backoff exponentiel.
"""

import time
import json
import re
import urllib.request
from youtube_transcript_api import YouTubeTranscriptApi


def _fetch_transcript_api(video_id: str, languages: list[str] = None) -> dict:
    """
    Méthode principale: youtube-transcript-api (fetch).
    Retourne {video_id, transcript, status, error}.
    """
    if languages is None:
        languages = ["en", "fr", "en-US"]

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        transcript = [
            {
                "start": snippet.start,
                "text": snippet.text,
                "duration": snippet.duration,
            }
            for snippet in fetched.snippets
        ]
        if transcript:
            return {
                "video_id": video_id,
                "transcript": transcript,
                "status": "OK",
                "error": None,
            }
        return {
            "video_id": video_id,
            "transcript": [],
            "status": "ECHEC",
            "error": "Transcript vide",
        }
    except Exception as e:
        return {
            "video_id": video_id,
            "transcript": [],
            "status": "ECHEC",
            "error": f"youtube-transcript-api: {str(e)[:200]}",
        }


def _fetch_transcript_fallback(video_id: str, languages: list[str] = None) -> dict:
    """
    Fallback: récupère le transcript via l'API timedtext de YouTube directement.
    Contourne les blocages IP en utilisant urllib avec headers navigateur.
    """
    if languages is None:
        languages = ["en", "fr"]

    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        m = re.search(r'"captionTracks":\s*(\[.*?\])', html)
        if not m:
            return {
                "video_id": video_id,
                "transcript": [],
                "status": "ECHEC",
                "error": "Aucun captionTracks trouvé dans la page",
            }

        caption_tracks = json.loads(m.group(1))

        track = None
        for lang in languages:
            for t in caption_tracks:
                if t.get("languageCode", "").startswith(lang):
                    track = t
                    break
            if track:
                break

        if not track and caption_tracks:
            track = caption_tracks[0]

        if not track:
            return {
                "video_id": video_id,
                "transcript": [],
                "status": "ECHEC",
                "error": "Aucune piste de sous-titres disponible",
            }

        caption_url = track.get("baseUrl", "")
        if not caption_url:
            return {
                "video_id": video_id,
                "transcript": [],
                "status": "ECHEC",
                "error": "URL du caption manquante",
            }

        if "fmt=" not in caption_url:
            caption_url += "&fmt=json3"

        req2 = urllib.request.Request(caption_url, headers=headers)
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data = json.loads(resp2.read().decode("utf-8", errors="replace"))

        transcript = []
        for event in data.get("events", []):
            if "segs" not in event:
                continue
            text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
            if not text:
                continue
            start_ms = event.get("tStartMs", 0)
            duration_ms = event.get("dDurationMs", 2000)
            transcript.append({
                "start": start_ms / 1000.0,
                "text": text,
                "duration": duration_ms / 1000.0,
            })

        if not transcript:
            return {
                "video_id": video_id,
                "transcript": [],
                "status": "ECHEC",
                "error": "Transcript vide après parsing",
            }

        return {
            "video_id": video_id,
            "transcript": transcript,
            "status": "OK",
            "error": None,
        }

    except Exception as e:
        return {
            "video_id": video_id,
            "transcript": [],
            "status": "ECHEC",
            "error": f"Fallback error: {str(e)[:200]}",
        }


def get_transcript(video_id: str, languages: list[str] = None, max_retries: int = 3) -> dict:
    """
    Récupère le transcript d'une vidéo avec timestamps.
    Essaie youtube-transcript-api d'abord, fallback sur API directe.
    Retry automatique sur rate-limit (429) avec backoff exponentiel.
    Retourne {video_id, transcript: [{start, text, duration}], status, error}.
    """
    if languages is None:
        languages = ["fr", "en", "en-US"]

    for attempt in range(max_retries):
        # Tentative 1: youtube-transcript-api
        result = _fetch_transcript_api(video_id, languages)
        if result["status"] == "OK":
            return result

        error_str = result.get("error", "")

        # Si c'est un rate-limit, on attend et on réessaie
        is_rate_limited = any(kw in error_str.lower() for kw in ["429", "too many", "rate limit"])
        if is_rate_limited and attempt < max_retries - 1:
            wait = (attempt + 1) * 10  # 10s, 20s, 30s
            print(f"   ⏳ Rate-limit détecté, attente {wait}s (tentative {attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue

        # Tentative 2: API timedtext directe
        print(f"   🔄 Fallback: API timedtext directe...")
        result = _fetch_transcript_fallback(video_id, languages)
        if result["status"] == "OK":
            return result

        # Si le fallback aussi rate-limited, retry
        if is_rate_limited and attempt < max_retries - 1:
            wait = (attempt + 1) * 10
            print(f"   ⏳ Fallback aussi limité, attente {wait}s...")
            time.sleep(wait)
            continue

        # Échec définitif
        return result

    return result


def run(videos: list[dict], delay: float = 3.0, languages: list[str] = None) -> dict:
    """
    Point d'entrée de la frégate SCRIBE.
    Prend la liste des vidéos de RECON, retourne les transcripts.
    Délai par défaut: 3s entre chaque vidéo pour éviter le rate-limit.
    """
    results = []
    success_count = 0
    fail_count = 0
    total_segments = 0
    langs_seen = set()

    total = len(videos)
    for i, video in enumerate(videos):
        vid = video.get("video_id")
        if not vid:
            continue

        print(f"   [{i+1}/{total}] {vid} — {video.get('title', '')[:50]}")

        transcript_data = get_transcript(vid, languages)
        results.append({
            "video_id": vid,
            "title": video.get("title", ""),
            "url": video.get("url", ""),
            "transcript": transcript_data["transcript"],
            "status": transcript_data["status"],
            "error": transcript_data["error"],
        })

        if transcript_data["status"] == "OK":
            success_count += 1
            total_segments += len(transcript_data["transcript"])
            print(f"        ✅ {len(transcript_data['transcript'])} segments")
        else:
            fail_count += 1
            print(f"        ❌ {transcript_data['error'][:80]}")

        # Délai anti rate-limit
        if i < total - 1:
            time.sleep(delay)

    return {
        "results": results,
        "meta": {
            "transcripts_recuperes": success_count,
            "transcripts_echoues": fail_count,
            "segments_totaux": total_segments,
            "langues": list(langs_seen),
        }
    }
