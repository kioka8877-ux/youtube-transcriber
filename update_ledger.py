#!/usr/bin/env python3
"""Update LEDGER.json with the final run results."""
import json
from datetime import datetime
from pathlib import Path

LEDGER_PATH = Path("/home/user/youtube-transcriber/LEDGER.json")
PROGRESS_PATH = Path("/home/user/youtube-transcriber/run_progress.json")

with open(LEDGER_PATH, "r", encoding="utf-8") as f:
    ledger = json.load(f)

with open(PROGRESS_PATH, "r") as f:
    progress = json.load(f)

ledger["statut"] = "VICTORIA_AETERNA"
ledger["gate_actuelle"] = "CLOSE"
ledger["production_title"] = "Stickman Hogwarts — Chaîne complète (128 vidéos)"
ledger["mode_execution"] = "sandbox"
ledger["recon_meta"] = {
    "videos_identifiees": 128,
    "duree_totale_sec": 117309
}
ledger["scribe_meta"] = {
    "transcripts_recuperes": progress["success"],
    "transcripts_echoues": progress["fail"],
    "segments_totaux": progress["segments"]
}
ledger["forge_meta"] = {
    "format_export": "txt",
    "taille_fichier_kb": progress["forge_size_kb"],
    "fichier_sortie": "exports/transcripts.txt"
}
ledger["artefacts"] = {
    "export_final": "exports/transcripts.txt"
}
ledger["derniere_mise_a_jour"] = datetime.now().astimezone().isoformat()

# Add session to history
session_id = f"YTT_{datetime.now().strftime('%Y%m%d_%H%M')}"
ledger["historique_sessions"].append({
    "session_id": session_id,
    "date": datetime.now().astimezone().isoformat(),
    "actions": [
        f"PORTE_1 validée: url=https://www.youtube.com/@StickmanHogwarts, format=txt, mode=sandbox",
        f"F01_RECON: 128 vidéos listées via YouTube Data API v3",
        f"PORTE_2 validée (champion): liste acceptée",
        f"F02_SCRIBE: {progress['success']} OK, {progress['fail']} échecs (yt-dlp subtitles)",
        f"PORTE_3 validée (champion): transcripts acceptés",
        f"F03_FORGE: export txt -> exports/transcripts.txt ({progress['forge_size_kb']} KB)",
        f"PORTE_4 validée (champion): artefact accepté. CLOSE.",
    ],
    "statut_session": "CLOSE"
})

with open(LEDGER_PATH, "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)

print("LEDGER updated ✅")
print(f"  Success: {progress['success']}/128")
print(f"  Segments: {progress['segments']}")
print(f"  Size: {progress['forge_size_kb']} KB")
