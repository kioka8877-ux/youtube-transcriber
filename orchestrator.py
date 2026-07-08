"""
orchestrator.py — Nerf central
Connaît l'état de chaque frégate, décide l'ordre d'exécution, gère les reprises.
Supporte deux modes: sandbox (interactif) et github (CI/CD).
"""

import json
import sys
import os
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


def run_pipeline(url: str, fmt: str = "json", delay: float = 2.0, languages: list = None, mode: str = "sandbox"):
    """
    Pipeline complet avec arrêt aux portes.
    L'Exécuteur tourne entre les portes, s'arrête à chaque porte.
    
    mode="sandbox": portes interactives (Champion valide dans le chat)
    mode="github": portes 2 et 3 auto-validées avec logging (CI/CD)
    """
    ledger = charger_ledger()
    ledger["mode_execution"] = mode
    sauver_ledger(ledger)

    # === PORTE 1: BRIEF ===
    print("🚪 PORTE 1 — BRIEF")
    print(f"   URL: {url}")
    print(f"   Format: {fmt}")
    print(f"   Mode: {mode}")
    valider_porte("PORTE_1_BRIEF", {"url": url, "format_export": fmt})
    ledger["gate_actuelle"] = "PORTE_1_BRIEF"
    ledger["statut"] = "EN_PRODUCTION"
    ledger["options_production"]["format_export"] = fmt
    ledger["options_production"]["delai_entre_requetes_sec"] = delay
    sauver_ledger(ledger)
    log_session(ledger, f"PORTE_1 validée: url={url}, format={fmt}, mode={mode}")

    # === F01 RECON ===
    print("\n🛰️  F01 RECON — Listing des vidéos...")
    recon_result = executer_frigate("F01_RECON", ledger, {"url": url})
    videos = recon_result["videos"]
    print(f"   → {len(videos)} vidéos trouvées")
    log_session(ledger, f"F01_RECON: {len(videos)} vidéos listées")

    # === PORTE 2: RECON ===
    if mode == "sandbox":
        print(f"\n🚪 PORTE 2 — RECON: {len(videos)} vidéos à valider")
        print("   Le Champion doit valider la liste, filtrer, exclure")
    else:
        print(f"\n🚪 PORTE 2 — RECON: AUTO-VALIDÉE (mode github)")
        print(f"   {len(videos)} vidéos — pas d'intervention Champion en CI")
    valider_porte("PORTE_2_RECON", {"validation_liste": True, "exclusions": [], "auto": mode == "github"})
    ledger["gate_actuelle"] = "PORTE_2_RECON"
    ledger["etapes_completees"].append("F01_RECON")
    sauver_ledger(ledger)
    log_session(ledger, f"PORTE_2 validée ({'auto' if mode == 'github' else 'champion'}): liste acceptée")

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
    if mode == "sandbox":
        print("\n🚪 PORTE 3 — SCRIBE: Le Champion doit vérifier la qualité")
    else:
        print("\n🚪 PORTE 3 — SCRIBE: AUTO-VALIDÉE (mode github)")
    valider_porte("PORTE_3_SCRIBE", {"validation_qualite": True, "corrections": [], "auto": mode == "github"})
    ledger["gate_actuelle"] = "PORTE_3_SCRIBE"
    ledger["etapes_completees"].append("F02_SCRIBE")
    sauver_ledger(ledger)
    log_session(ledger, f"PORTE_3 validée ({'auto' if mode == 'github' else 'champion'}): transcripts acceptés")

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
    if mode == "sandbox":
        print(f"\n🚪 PORTE 4 — FORGE: Artefact {output_path}")
        print("   Le Champion doit valider l'artefact final")
    else:
        print(f"\n🚪 PORTE 4 — FORGE: AUTO-VALIDÉE (mode github)")
        print(f"   Artefact: {output_path} — Champion review post-run")
    valider_porte("PORTE_4_FORGE", {"validation_artefact": True, "publication": False, "auto": mode == "github"})
    ledger["gate_actuelle"] = "CLOSE"
    ledger["statut"] = "VICTORIA_AETERNA"
    ledger["etapes_completees"].append("CLOSE")
    sauver_ledger(ledger)
    log_session(ledger, f"PORTE_4 validée ({'auto' if mode == 'github' else 'champion'}): artefact accepté. CLOSE.")

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
    # Support env vars pour GitHub Actions
    url = os.environ.get("INPUT_URL") or os.environ.get("YTT_URL")
    fmt = os.environ.get("INPUT_FORMAT") or os.environ.get("YTT_FORMAT", "json")
    mode = os.environ.get("INPUT_MODE") or os.environ.get("YTT_MODE", "sandbox")
    langs_str = os.environ.get("INPUT_LANGUAGES") or os.environ.get("YTT_LANGUAGES", "fr,en")
    languages = langs_str.split(",") if langs_str else ["fr", "en"]

    if "--resume" in sys.argv:
        resume()
    elif "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        mode = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "sandbox"
        # URL est le premier arg non-flag
        args = [a for a in sys.argv[1:] if not a.startswith("-") and a != mode]
        if args:
            url = args[0]
            fmt = args[1] if len(args) > 1 else fmt
            run_pipeline(url, fmt, languages=languages, mode=mode)
        else:
            print(f"Usage: python orchestrator.py <url> [json|srt|txt] --mode sandbox|github")
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        url = sys.argv[1]
        fmt = sys.argv[2] if len(sys.argv) >= 3 else "json"
        run_pipeline(url, fmt, languages=languages, mode=mode)
    elif url:
        # Mode GitHub Actions via env vars
        run_pipeline(url, fmt, languages=languages, mode=mode)
    else:
        print("Usage: python orchestrator.py <url> [json|srt|txt] [--mode sandbox|github]")
        print("       python orchestrator.py --resume")
        print("       Env vars: INPUT_URL, INPUT_FORMAT, INPUT_MODE, INPUT_LANGUAGES")
