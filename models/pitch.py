from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Pydantic schemas (API I/O) ────────────────────────

class PitchExtractedData(BaseModel):
    """Données structurées extraites du pitch deck par le LLM"""
    startup_name: str
    industry: str                    # ex: "FinTech", "GreenTech", "HealthTech"
    stage: str                       # ex: "Idea", "MVP", "Seed", "Series A"
    country: str
    problem: str                     # Le problème que le startup résout
    solution: str                    # La solution proposée
    market_size: str                 # TAM/SAM/SOM
    business_model: str              # Comment le startup gagne de l'argent
    team: str                        # Description de l'équipe
    traction: Optional[str] = None   # Métriques, clients, revenus
    funding_needed: Optional[str] = None  # Montant recherché
    keywords: list[str] = []         # Mots-clés pour la recherche de grants
    raw_text: str = ""               # Texte brut extrait du fichier


class PitchUploadResponse(BaseModel):
    """Réponse après upload d'un pitch deck"""
    pitch_id: str
    filename: str
    status: str                      # "processing" | "completed" | "failed"
    extracted_data: Optional[PitchExtractedData] = None
    message: str = ""


class PitchListItem(BaseModel):
    """Item dans la liste des pitch decks"""
    pitch_id: str
    filename: str
    startup_name: str
    industry: str
    stage: str
    created_at: datetime
    status: str
