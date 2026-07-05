"""
orchestrator.py — Nerf central
Connaît l'état de chaque frégate, décide l'ordre d'exécution, gère les reprises.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from gates import PORTES, ORDRE_PORTES, ouvrir_porte, valider_porte, porte_suivante, portes_to_dict
from fregate import RECON, SCRIBE, FORGE


LEDGER_PATH = Path(__file__).parent / "LEDGER.json"
EXPORTS_DIR = Path(__file__).parent / "exports"


def charger_ledger() -> dict:
    """Charge le ledger depuis le disque."""
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sauver_ledger(ledger: dict):
    """Sauvegarde le ledger sur disque."""
    ledger["derniere_mise_a_jour"] = datetime.now().astimezone().isoformat()
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def log_session(ledger: dict, action: str):
    """Ajoute une action à l'historique de session."""
    session_id = ledger.get("run_id", "UNKNOWN")
    for session in ledger.get("historique_sessions", []):
        if session.get("session_id") == session_id:
            session.setdefault("actions", []).append(action)
            break
    sauver_ledger(ledger)


def executer_frigate(frigate_name: str, ledger: dict, inputs: dict) -> dict:
    """
    Exécute une frégate selon son nom.
    Retourne le résultat de la frégate.
    """
    if frigate_name == "F01_RECON":
        url = inputs.get("url")
        if not url:
            raise ValueError("URL manquante pour RECON")
        result = RECON.run(url)
        ledger["recon_meta"] = result["meta"]
        ledger["territory"] = {
            "url_cible": url,
            "type": None,
            "channel_name": None,
            "video_count": result["meta"]["video_count"],
        }
        return result

    elif frigate_name == "F02_SCRIBE":
        videos = inputs.get("videos", [])
        delay = inputs.get("delay", 2.0)
        languages = inputs.get("languages", ["fr", "en"])
        result = SCRIBE.run(videos, delay, languages)
        ledger["scribe_meta"] = result["meta"]
        return result

    elif frigate_name == "F03_FORGE":
        results = inputs.get("results", [])
        fmt = inputs.get("format", "json")
        result = FORGE.run(results, fmt)
        ledger["forge_meta"] = result["meta"]
        return result

    else:
        raise ValueError(f"Frégate inconnue: {frigate_name}")


def run_pipeline(url: str, fmt: str = "json", delay: float = 2.0, languages: list = None):
    """
    Pipeline complet avec arrêt aux portes.
    L'Exécuteur tourne entre les portes, s'arrête à chaque porte.
    """
    ledger = charger_ledger()

    # === PORTE 1: BRIEF ===
    print("🚪 PORTE 1 — BRIEF: En attente du Champion")
    print(f"   URL: {url}")
    print(f"   Format: {fmt}")
    valider_porte("PORTE_1_BRIEF", {"url": url, "format_export": fmt})
    ledger["gate_actuelle"] = "PORTE_1_BRIEF"
    ledger["statut"] = "EN_PRODUCTION"
    ledger["options_production"]["format_export"] = fmt
    ledger["options_production"]["delai_entre_requetes_sec"] = delay
    sauver_ledger(ledger)
    log_session(ledger, f"PORTE_1 validée: url={url}, format={fmt}")

    # === F01 RECON ===
    print("\n🛰️  F01 RECON — Listing des vidéos...")
    recon_result = executer_frigate("F01_RECON", ledger, {"url": url})
    videos = recon_result["videos"]
    print(f"   → {len(videos)} vidéos trouvées")
    log_session(ledger, f"F01_RECON: {len(videos)} vidéos listées")

    # === PORTE 2: RECON ===
    print("\n🚪 PORTE 2 — RECON: En attente du Champion")
    print(f"   {len(videos)} vidéos à valider")
    print("   Le Champion doit valider la liste, filtrer, exclure")
    valider_porte("PORTE_2_RECON", {"validation_liste": True, "exclusions": []})
    ledger["gate_actuelle"] = "PORTE_2_RECON"
    ledger["etapes_completees"].append("F01_RECON")
    sauver_ledger(ledger)
    log_session(ledger, "PORTE_2 validée: liste acceptée")

    # === F02 SCRIBE ===
    print("\n✍️  F02 SCRIBE — Extraction des transcripts...")
    scribe_result = executer_frigate("F02_SCRIBE", ledger, {
        "videos": videos,
        "delay": delay,
        "languages": languages or ["fr", "en"],
    })
    print(f"   → {scribe_result['meta']['transcripts_recuperes']} transcripts récupérés")
    print(f"   → {scribe_result['meta']['transcripts_echoues']} échecs")
    log_session(ledger, f"F02_SCRIBE: {scribe_result['meta']['transcripts_recuperes']} OK, {scribe_result['meta']['transcripts_echoues']} échecs")

    # === PORTE 3: SCRIBE ===
    print("\n🚪 PORTE 3 — SCRIBE: En attente du Champion")
    print("   Le Champion doit vérifier la qualité des transcripts")
    valider_porte("PORTE_3_SCRIBE", {"validation_qualite": True, "corrections": []})
    ledger["gate_actuelle"] = "PORTE_3_SCRIBE"
    ledger["etapes_completees"].append("F02_SCRIBE")
    sauver_ledger(ledger)
    log_session(ledger, "PORTE_3 validée: transcripts acceptés")

    # === F03 FORGE ===
    print(f"\n🔨 F03 FORGE — Export en {fmt.upper()}...")
    forge_result = executer_frigate("F03_FORGE", ledger, {
        "results": scribe_result["results"],
        "format": fmt,
    })

    # Sauvegarder le fichier d'export
    EXPORTS_DIR.mkdir(exist_ok=True)
    output_path = EXPORTS_DIR / forge_result["filename"]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(forge_result["content"])
    print(f"   → Fichier: {output_path} ({forge_result['meta']['taille_fichier_kb']} KB)")

    ledger["artefacts"]["export_final"] = str(output_path)
    ledger["etapes_completees"].append("F03_FORGE")
    log_session(ledger, f"F03_FORGE: export {fmt} -> {output_path}")

    # === PORTE 4: FORGE ===
    print("\n🚪 PORTE 4 — FORGE: En attente du Champion")
    print(f"   Artefact: {output_path}")
    print("   Le Champion doit valider l'artefact final")
    valider_porte("PORTE_4_FORGE", {"validation_artefact": True, "publication": False})
    ledger["gate_actuelle"] = "CLOSE"
    ledger["statut"] = "VICTORIA_AETERNA"
    ledger["etapes_completees"].append("CLOSE")
    sauver_ledger(ledger)
    log_session(ledger, "PORTE_4 validée: artefact accepté. CLOSE.")

    print("\n✅ Pipeline terminé. Statut: VICTORIA_AETERNA")
    print(f"   Artefact: {output_path}")

    return forge_result


def resume():
    """
    Reprise depuis le ledger. Lit gate_actuelle et continue.
    """
    ledger = charger_ledger()
    gate = ledger.get("gate_actuelle", "PORTE_1_BRIEF")
    print(f"📋 Reprise — Gate actuelle: {gate}")
    print(f"   Étapes complétées: {ledger.get('etapes_completees', [])}")
    print(f"   Statut: {ledger.get('statut', 'INCONNU')}")

    if ledger.get("statut") == "VICTORIA_AETERNA":
        print("   → Pipeline déjà terminé.")
        return

    print("   → Utiliser run_pipeline() pour relancer depuis le début")
    print("   → Ou fournir les inputs manquants pour continuer")


if __name__ == "__main__":
    if "--resume" in sys.argv:
        resume()
    elif len(sys.argv) >= 2:
        url = sys.argv[1]
        fmt = sys.argv[2] if len(sys.argv) >= 3 else "json"
        run_pipeline(url, fmt)
    else:
        print("Usage: python orchestrator.py <url> [json|srt|txt]")
        print("       python orchestrator.py --resume")
