from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class SubmissionStatus(str, Enum):
    PENDING    = "pending"
    ADAPTING   = "adapting"       # LLM adapte le contenu
    NAVIGATING = "navigating"     # Browser Agent navigue vers le portail
    FILLING    = "filling"        # Remplissage du formulaire
    REVIEWING  = "reviewing"      # Validation avant soumission
    SUBMITTED  = "submitted"      # Soumis avec succès
    FAILED     = "failed"         # Erreur
    BLOCKED    = "blocked"        # Intervention manuelle requise (captcha...)


class SubmissionRequest(BaseModel):
    """Lancer une soumission autonome"""
    pitch_id: str
    grant_id: str
    approved_draft: Optional[str] = None  # Si l'utilisateur a modifié le brouillon


class SubmissionStatusUpdate(BaseModel):
    """Mise à jour du statut en temps réel (WebSocket)"""
    submission_id: str
    status: SubmissionStatus
    message: str                          # Message lisible par l'utilisateur
    progress: int = 0                     # 0-100
    screenshot_url: Optional[str] = None  # Capture du Browser Agent
    error: Optional[str] = None


class SubmissionResult(BaseModel):
    """Résultat final d'une soumission"""
    submission_id: str
    pitch_id: str
    grant_id: str
    grant_name: str
    status: SubmissionStatus
    reference_id: Optional[str] = None   # ID de confirmation du portail
    submitted_at: Optional[datetime] = None
    error_details: Optional[str] = None
    draft_used: str = ""                  # Le contenu soumis
