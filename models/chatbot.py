from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── DB Representation Models ───────────────────────────

class ChatbotConversationDB(BaseModel):
    """Modèle conversation pour la base de données"""
    id: int
    conversation_id: str
    user_id: Optional[int] = None
    pitch_id: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    evaluation_scores: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatbotFeedbackDB(BaseModel):
    """Modèle feedback pour la base de données"""
    id: int
    conversation_id: str
    user_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
