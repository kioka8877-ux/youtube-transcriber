#!/usr/bin/env python3
"""Run full pipeline on @StickmanHogwarts — 128 videos. Uses yt-dlp for subtitles."""
import sys, os, json, time, subprocess, tempfile, re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['YOUTUBE_API_KEY'] = 'AIzaSyCvSakdTIOQXwpkchEI6WlH4kE5VDFX3lk'

from fregate import RECON, FORGE

LOG_FILE = Path(__file__).parent / "run_progress.json"
EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

def save_progress(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_transcript_ytdlp(video_id, languages=None):
    """Fetch transcript via yt-dlp --write-auto-subs."""
    if languages is None:
        languages = ["en"]
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    lang_str = ",".join(languages)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "sub")
        cmd = [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-lang", lang_str,
            "--sub-format", "json3",
            "--skip-download",
            "--no-warnings",
            "-o", outtmpl,
            url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return [], "ECHEC", "yt-dlp timeout"
        
        # Find the subtitle file
        sub_files = [f for f in os.listdir(tmpdir) if f.endswith(".json3")]
        if not sub_files:
            # Try vtt
            sub_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
            if not sub_files:
                err = result.stderr[:200] if result.stderr else "no file"
                return [], "ECHEC", f"yt-dlp: no subtitle file. stderr: {err}"
        
        sub_path = os.path.join(tmpdir, sub_files[0])
        
        if sub_path.endswith(".json3"):
            with open(sub_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            transcript = []
            for event in data.get("events", []):
                if "segs" not in event:
                    continue
                text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
                if text:
                    transcript.append({
                        "start": event.get("tStartMs", 0) / 1000.0,
                        "text": text,
                        "duration": event.get("dDurationMs", 2000) / 1000.0,
                    })
            if transcript:
                return transcript, "OK", None
            return [], "ECHEC", "yt-dlp: empty transcript after parse"
        
        # VTT fallback
        elif sub_path.endswith(".vtt"):
            transcript = []
            with open(sub_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            current_start = 0
            current_duration = 2.0
            text_buffer = []
            for line in lines:
                line = line.strip()
                if "-->" in line:
                    if text_buffer:
                        text = " ".join(text_buffer).strip()
                        if text:
                            transcript.append({"start": current_start, "text": text, "duration": current_duration})
                        text_buffer = []
                    times = line.split("-->")
                    current_start = _parse_vtt_time(times[0].strip())
                    end = _parse_vtt_time(times[1].strip().split(" ")[0])
                    current_duration = end - current_start
                elif line and not line.isdigit() and "WEBVTT" not in line:
                    text_buffer.append(line)
            if text_buffer:
                text = " ".join(text_buffer).strip()
                if text:
                    transcript.append({"start": current_start, "text": text, "duration": current_duration})
            if transcript:
                return transcript, "OK", None
            return [], "ECHEC", "yt-dlp: empty vtt after parse"
    
    return [], "ECHEC", "yt-dlp: unexpected failure"

def _parse_vtt_time(time_str):
    parts = time_str.replace(",", ".").split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])

# === F01 RECON ===
print("🛰️  F01 RECON — Listing des vidéos...", flush=True)
recon_result = RECON.run("https://www.youtube.com/@StickmanHogwarts")
videos = recon_result["videos"]
print(f"   → {len(videos)} vidéos trouvées", flush=True)

progress = {
    "etape": "RECON_DONE",
    "total_videos": len(videos),
    "scribe_progress": 0,
    "success": 0,
    "fail": 0,
    "segments": 0,
    "errors": [],
    "started_at": datetime.now().astimezone().isoformat(),
}
save_progress(progress)

# === F02 SCRIBE ===
print(f"\n✍️  F02 SCRIBE — Extraction via yt-dlp (délai 3s)...", flush=True)

results = []
success_count = 0
fail_count = 0
total_segments = 0

for i, video in enumerate(videos):
    vid = video.get("video_id")
    if not vid:
        continue

    transcript, status, error = fetch_transcript_ytdlp(vid, ["en"])
    
    results.append({
        "video_id": vid,
        "title": video.get("title", ""),
        "url": video.get("url", ""),
        "transcript": transcript,
        "status": status,
        "error": error,
    })

    if status == "OK":
        success_count += 1
        total_segments += len(transcript)
        marker = "✅"
    else:
        fail_count += 1
        marker = "❌"
        progress["errors"].append({"video_id": vid, "title": video.get("title", ""), "error": error})

    print(f"   [{i+1}/{len(videos)}] {marker} {vid} | {len(transcript)} seg | {video.get('title', '')[:50]}", flush=True)

    # Save progress every 5 videos
    if (i + 1) % 5 == 0 or i == len(videos) - 1:
        progress["scribe_progress"] = i + 1
        progress["success"] = success_count
        progress["fail"] = fail_count
        progress["segments"] = total_segments
        save_progress(progress)

    # Délai anti rate-limit
    if i < len(videos) - 1:
        time.sleep(3)

print(f"\n   → {success_count} OK, {fail_count} échecs, {total_segments} segments", flush=True)

# === F03 FORGE ===
print(f"\n🔨 F03 FORGE — Export TXT...", flush=True)
forge_result = FORGE.run(results, "txt")
output_path = EXPORTS_DIR / forge_result["filename"]
with open(output_path, "w", encoding="utf-8") as f:
    f.write(forge_result["content"])
print(f"   → {output_path} ({forge_result['meta']['taille_fichier_kb']} KB)", flush=True)

# Final progress
progress["etape"] = "VICTORIA_AETERNA"
progress["forge_size_kb"] = forge_result["meta"]["taille_fichier_kb"]
progress["forge_file"] = str(output_path)
progress["finished_at"] = datetime.now().astimezone().isoformat()
save_progress(progress)

print(f"\n✅ VICTORIA_AETERNA — Pipeline terminé", flush=True)
print(f"   {success_count}/{len(videos)} transcripts | {total_segments} segments | {forge_result['meta']['taille_fichier_kb']} KB", flush=True)
