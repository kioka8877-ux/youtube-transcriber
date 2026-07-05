"""
F03_FORGE — Frégate de forge
Exporte les transcripts en JSON, SRT ou TXT.
"""

import json
from datetime import timedelta


def _format_srt_time(seconds: float) -> str:
    """Convertit des secondes en format SRT: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_ms = int(td.total_seconds() * 1000)
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def export_json(results: list[dict]) -> str:
    """Export en JSON structuré."""
    output = []
    for r in results:
        if r["status"] != "OK":
            continue
        output.append({
            "video_id": r["video_id"],
            "title": r["title"],
            "url": r["url"],
            "transcript": r["transcript"],
        })
    return json.dumps(output, ensure_ascii=False, indent=2)


def export_srt(results: list[dict]) -> str:
    """Export en SRT (sous-titres standard)."""
    lines = []
    counter = 1
    for r in results:
        if r["status"] != "OK":
            continue
        for seg in r["transcript"]:
            start = seg.get("start", 0)
            duration = seg.get("duration", 2.0)
            end = start + duration
            text = seg.get("text", "").strip()
            if not text:
                continue
            lines.append(str(counter))
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.append(text)
            lines.append("")
            counter += 1
    return "\n".join(lines)


def export_txt(results: list[dict]) -> str:
    """Export en texte brut."""
    lines = []
    for r in results:
        if r["status"] != "OK":
            continue
        lines.append(f"=== {r['title']} ===")
        lines.append(r["url"])
        lines.append("")
        text = " ".join(seg.get("text", "").strip() for seg in r["transcript"])
        lines.append(text)
        lines.append("")
        lines.append("")
    return "\n".join(lines)


def run(results: list[dict], fmt: str = "json") -> dict:
    """
    Point d'entrée de la frégate FORGE.
    Retourne {content, format, filename, meta}.
    """
    fmt = fmt.lower().strip()

    if fmt == "json":
        content = export_json(results)
        filename = "transcripts.json"
    elif fmt == "srt":
        content = export_srt(results)
        filename = "transcripts.srt"
    elif fmt == "txt":
        content = export_txt(results)
        filename = "transcripts.txt"
    else:
        raise ValueError(f"Format non supporté: {fmt}. Utiliser json, srt ou txt.")

    size_kb = len(content.encode("utf-8")) / 1024

    return {
        "content": content,
        "format": fmt,
        "filename": filename,
        "meta": {
            "format_export": fmt,
            "taille_fichier_kb": round(size_kb, 2),
            "fichier_sortie": filename,
        }
    }
