from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from core.database import Base


class GrantDB(Base):
    """SQLAlchemy model for storing grants in database"""
    __tablename__ = "grants"
    
    id = Column(Integer, primary_key=True, index=True)
    grant_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    organization = Column(String)
    portal = Column(String)
    portal_url = Column(String)
    description = Column(Text)
    eligibility = Column(Text)
    funding_amount = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    industry_focus = Column(JSON)
    stage_focus = Column(JSON)
    country_focus = Column(JSON)
    
    vibe = Column(String, default="innovation")
    relevance_score = Column(Float, default=0.0)
    source = Column(String, default="")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Grant {self.name}>"


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
