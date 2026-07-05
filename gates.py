"""
gates.py — Les quatre portes
Moments de souveraineté humaine. L'Exécuteur s'arrête à chaque porte.
"""


class Gate:
    """Représente une porte de souveraineté."""

    def __init__(self, gate_id: str, description: str, inputs_attendus: list[str]):
        self.gate_id = gate_id
        self.description = description
        self.inputs_attendus = inputs_attendus
        self.statut = "VERROUILLEE"
        self.inputs = {}

    def ouvrir(self):
        """Ouvre la porte — l'Exécuteur s'arrête et attend le Champion."""
        self.statut = "EN_ATTENTE"

    def valider(self, inputs: dict):
        """Le Champion fournit ses inputs et verrouille la porte."""
        self.inputs = inputs
        self.statut = "VERROUILLEE"

    def is_open(self) -> bool:
        return self.statut == "EN_ATTENTE"

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "statut": self.statut,
            "inputs_attendus": self.inputs_attendus,
            "inputs": self.inputs,
        }


# Les quatre portes doctrinales
PORTES = {
    "PORTE_1_BRIEF": Gate(
        "PORTE_1_BRIEF",
        "Champion fournit l'URL cible, le format d'export et les options",
        ["url", "format_export", "options"],
    ),
    "PORTE_2_RECON": Gate(
        "PORTE_2_RECON",
        "Champion valide la liste des vidéos, filtre, exclut",
        ["validation_liste", "exclusions"],
    ),
    "PORTE_3_SCRIBE": Gate(
        "PORTE_3_SCRIBE",
        "Champion vérifie la qualité des transcripts, comble les gaps",
        ["validation_qualite", "corrections"],
    ),
    "PORTE_4_FORGE": Gate(
        "PORTE_4_FORGE",
        "Champion valide l'artefact final, publie",
        ["validation_artefact", "publication"],
    ),
}

# Ordre d'exécution
ORDRE_PORTES = ["PORTE_1_BRIEF", "PORTE_2_RECON", "PORTE_3_SCRIBE", "PORTE_4_FORGE"]


def ouvrir_porte(gate_id: str):
    """Ouvre une porte spécifique."""
    if gate_id not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[gate_id].ouvrir()


def valider_porte(gate_id: str, inputs: dict):
    """Le Champion valide une porte avec ses inputs."""
    if gate_id not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[gate_id].valider(inputs)


def porte_suivante(gate_actuelle: str) -> str | None:
    """Retourne la porte suivante, ou None si on est à la dernière."""
    if gate_actuelle is None:
        return ORDRE_PORTES[0]
    idx = ORDRE_PORTES.index(gate_actuelle) if gate_actuelle in ORDRE_PORTES else -1
    if idx + 1 < len(ORDRE_PORTES):
        return ORDRE_PORTES[idx + 1]
    return None


def portes_to_dict() -> dict:
    """Sérialise l'état des portes pour le ledger."""
    return {gid: gate.to_dict() for gid, gate in PORTES.items()}
