from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Message ────────────────────────────────────────────

class ChatMessage(BaseModel):
    """Un message dans une conversation"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[datetime] = None


# ── Evaluation ─────────────────────────────────────────

class EvaluationCriteria(BaseModel):
    """Score et feedback pour un critère d'évaluation"""
    criterion: str
    score: float = Field(..., ge=0, le=10)
    feedback: str


class EvaluatePitchRequest(BaseModel):
    """Requête d'évaluation d'un pitch deck"""
    pitch_id: str
    language: Optional[str] = "fr"


class EvaluatePitchResponse(BaseModel):
    """Réponse d'évaluation d'un pitch deck"""
    conversation_id: str
    pitch_id: str
    overall_score: float
    criteria: List[EvaluationCriteria]
    recommendations: List[str]
    summary: str


# ── Chat ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Requête d'envoi d'un message"""
    message: str
    conversation_id: Optional[str] = None
    pitch_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Réponse à un message de chat"""
    conversation_id: str
    message: str
    role: str = "assistant"
    timestamp: datetime


# ── Conversation ───────────────────────────────────────

class ConversationResponse(BaseModel):
    """Historique complet d'une conversation"""
    conversation_id: str
    pitch_id: Optional[str] = None
    messages: List[ChatMessage]
    evaluation_scores: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Feedback ───────────────────────────────────────────

class FeedbackRequest(BaseModel):
    """Requête d'ajout de feedback"""
    conversation_id: str
    rating: int = Field(..., ge=1, le=5, description="Note de 1 à 5 étoiles")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Réponse après ajout du feedback"""
    success: bool
    message: str
    feedback_id: int
