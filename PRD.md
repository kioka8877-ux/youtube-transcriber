# 📋 PRD — YouTube/TikTok Transcriber

## 1. Vision

Un outil permettant de scraper les vidéos d'une chaîne YouTube (ou une vidéo unique) et d'en extraire les transcriptions avec timestamps, puis d'exporter le tout en JSON, SRT ou TXT.

## 2. Objectifs

- **Lister** les vidéos d'une chaîne YouTube entière ou d'une vidéo unique
- **Transcrire** chaque vidéo avec timestamps précis
- **Exporter** en 3 formats : JSON structuré, SRT (sous-titres), TXT (brut)
- **Autonomie** : pipeline autonome entre les portes, Champion aux portes uniquement

## 3. Fonctionnalités

### Must-have (MVP)
| ID | Feature | Description |
|----|---------|-------------|
| F1 | Input URL | Accepter une URL YouTube (vidéo ou chaîne) |
| F2 | Scraper chaîne | Lister toutes les vidéos d'une chaîne via yt-dlp |
| F3 | Transcription | Récupérer les transcripts avec timestamps via youtube-transcript-api |
| F4 | Export JSON | Export structuré : {video_id, title, url, transcript: [{start, text, duration}]} |
| F5 | Export SRT | Format sous-titres standard |
| F6 | Export TXT | Texte brut concaténé |

### Nice-to-have (V2)
| ID | Feature | Description |
|----|---------|-------------|
| F7 | Support TikTok | Scraper transcription TikTok (Playwright) |
| F8 | Cache | Éviter de re-scraper la même chaîne |
| F9 | Filtrage | Filtrer par date / mots-clés / durée |
| F10 | Langue auto | Détection de langue de la transcription |

## 4. Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.10+ |
| Scraping vidéos | yt-dlp |
| Transcription | youtube-transcript-api |
| Export | stdlib (json, datetime) |
| Cache | json sur disque |

## 5. Architecture (Media Pipeline Architecture)

- **3 frégates** : RECON (listing) → SCRIBE (transcription) → FORGE (export)
- **4 portes** : Brief → Recon → Scribe → Forge
- **1 orchestrateur** : nerf central, connaît l'état de chaque frégate
- **1 ledger** : LEDGER.json, mémoire nomadique

## 6. Formats de sortie

### JSON
```json
[
  {
    "video_id": "abc123",
    "title": "Titre de la vidéo",
    "url": "https://youtube.com/watch?v=abc123",
    "transcript": [
      {"start": 0.0, "text": "Bonjour...", "duration": 5.2}
    ]
  }
]
```

### SRT
```
1
00:00:00,000 --> 00:00:05,200
Bonjour...

2
00:00:05,200 --> 00:00:10,000
Aujourd'hui...
```

### TXT
```
=== Titre de la vidéo ===
Bonjour... Aujourd'hui...
```

## 7. Limitations

- YouTube peut bloquer le scraping intensif (rate limiting)
- Certaines vidéos n'ont pas de transcription disponible
- TikTok nécessite un navigateur headless (V2)

## 8. Milestones

| Milestone | Contenu | Statut |
|-----------|---------|--------|
| M0 | Structure projet + LEDGER + PRD + README | ✅ |
| M1 | validators.py + RECON.py | ⬜ |
| M2 | SCRIBE.py | ⬜ |
| M3 | FORGE.py | ⬜ |
| M4 | gates.py + orchestrator.py | ⬜ |
| M5 | Tests | ⬜ |
| M6 | Test production | ⬜ |
