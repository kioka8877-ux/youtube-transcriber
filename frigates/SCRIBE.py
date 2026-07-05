"""
F02_SCRIBE — Frégate de transcription
Extrait les transcriptions avec timestamps via youtube-transcript-api.
"""

import time
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, languages: list[str] = None) -> dict:
    """
    Récupère le transcript d'une vidéo avec timestamps.
    Retourne {video_id, transcript: [{start, text, duration}], status, error}.
    """
    if languages is None:
        languages = ["fr", "en", "en-US"]

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
            "error": str(e),
        }


def run(videos: list[dict], delay: float = 2.0, languages: list[str] = None) -> dict:
    """
    Point d'entrée de la frégate SCRIBE.
    Prend la liste des vidéos de RECON, retourne les transcripts.
    """
    results = []
    success_count = 0
    fail_count = 0
    total_segments = 0
    langs_seen = set()

    for i, video in enumerate(videos):
        vid = video.get("video_id")
        if not vid:
            continue

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
        else:
            fail_count += 1

        # Délai anti rate-limit
        if i < len(videos) - 1:
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
