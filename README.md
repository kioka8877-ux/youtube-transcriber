# 🎬 YouTube/TikTok Transcriber

Un outil Python pour scraper les vidéos d'une chaîne YouTube (ou une vidéo unique) et en extraire les transcriptions avec timestamps, puis exporter le tout en JSON, SRT ou TXT.

## 🏗️ Architecture

Ce projet suit la doctrine **Media Pipeline Architecture** :
- **3 frégates** (organes autonomes) : RECON → SCRIBE → FORGE
- **4 portes** (souveraineté humaine) : Brief → Recon → Scribe → Forge
- **1 orchestrateur** (nerf central)
- **1 ledger** (mémoire nomadique en JSON)

## 🚀 Installation

```bash
cd youtube_transcriber
pip install -r requirements.txt
```

## 📖 Utilisation

```bash
# Pipeline complet
python orchestrator.py "https://youtube.com/watch?v=..." json

# Reprise depuis le ledger
python orchestrator.py --resume
```

## 🗂️ Structure

```
youtube_transcriber/
├── LEDGER.json              Mémoire nomadique
├── PRD.md                   Cahier des charges
├── README.md                Ce fichier
├── requirements.txt         Dépendances
├── orchestrator.py          Nerf central
├── gates.py                 Les 4 portes
├── fregate/
│   ├── RECON.py             F01: liste les vidéos (yt-dlp)
│   ├── SCRIBE.py            F02: extrait les transcripts
│   └── FORGE.py             F03: export JSON/SRT/TXT
├── utils/
│   ├── validators.py        Validation d'URLs
│   └── cache.py             Cache disque
├── exports/                 Fichiers générés
└── tests/
```

## 📤 Formats de sortie

- **JSON** : structuré avec video_id, title, url, transcript
- **SRT** : sous-titres standard avec timestamps
- **TXT** : texte brut concaténé

## 📄 Documentation

- [`PRD.md`](PRD.md) — Cahier des charges
- [`LEDGER.json`](LEDGER.json) — État courant du projet
