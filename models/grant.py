from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Grant(BaseModel):
    """Un grant ou compétition trouvé par l'agent"""
    grant_id: str
    name: str
    organization: str                # Ex: "European Commission", "Y Combinator"
    portal: str                      # Ex: "F6S", "Gust", "custom"
    portal_url: str                  # URL du formulaire de soumission
    description: str
    eligibility: str                 # Critères d'éligibilité
    funding_amount: Optional[str] = None
    deadline: Optional[datetime] = None
    industry_focus: list[str] = []   # Ex: ["GreenTech", "CleanEnergy"]
    stage_focus: list[str] = []      # Ex: ["Seed", "MVP"]
    country_focus: list[str] = []    # Ex: ["Tunisia", "Global"]
    vibe: str = "innovation"         # "impact" | "innovation" | "greentech" | "social"
    relevance_score: float = 0.0     # Score de pertinence calculé par l'agent (0-1)
    source: str = ""                 # D'où vient ce grant (web search, F6S...)


class GrantSearchRequest(BaseModel):
    """Requête de recherche de grants"""
    pitch_id: str
    industry: str
    stage: str
    country: str
    keywords: list[str] = []
    max_results: int = 20


class GrantSearchResponse(BaseModel):
    """Résultat de la recherche de grants"""
    total_found: int
    grants: list[Grant]
    search_duration_seconds: float
