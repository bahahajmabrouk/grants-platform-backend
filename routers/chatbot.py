import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.chatbot_schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    EvaluatePitchRequest,
    EvaluatePitchResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from services.auth import verify_token
from services.chatbot import ChatbotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


# ── Helper: optional auth ──────────────────────────────

def _optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[int]:
    """Extrait l'user_id du header Authorization si présent (non bloquant)."""
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() == "bearer":
            return verify_token(token)
    except Exception:
        pass
    return None


# ── EVALUATE ──────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluatePitchResponse)
async def evaluate_pitch(
    request: EvaluatePitchRequest,
    db: Session = Depends(get_db),
):
    """
    🤖 Évaluer un pitch deck sur 6 critères via Ollama.

    Critères :
    1. Clarté du marché et opportunité
    2. Adéquation problème/solution
    3. Expérience et expertise de l'équipe
    4. Avantage concurrentiel
    5. Traction et métriques
    6. Clarté des besoins de financement

    Retourne les scores, recommandations actionnables et un résumé global.
    Crée également une conversation persistée pour le suivi.
    """
    try:
        service = ChatbotService(db)
        return await service.evaluate_pitch(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("❌ Erreur évaluation pitch %s: %s", request.pitch_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── CHAT ──────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    💬 Envoyer un message au chatbot.

    Si `conversation_id` est fourni, le message est ajouté à la conversation
    existante. Sinon, une nouvelle conversation est créée.

    Optionnellement, liez la conversation à un pitch via `pitch_id` pour que
    le chatbot dispose du contexte de la startup.
    """
    try:
        service = ChatbotService(db)
        return await service.chat(request)
    except Exception as exc:
        logger.error("❌ Erreur chat: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── CONVERSATION HISTORY ──────────────────────────────

@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """
    📜 Récupérer l'historique d'une conversation.

    Retourne tous les messages de la conversation ainsi que les scores
    d'évaluation si la conversation est liée à une évaluation de pitch.
    """
    service = ChatbotService(db)
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation '{conversation_id}' introuvable.",
        )

    messages = [
        ChatMessage(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            timestamp=msg.get("timestamp"),
        )
        for msg in (conversation.messages or [])
    ]

    return ConversationResponse(
        conversation_id=conversation.conversation_id,
        pitch_id=conversation.pitch_id,
        messages=messages,
        evaluation_scores=conversation.evaluation_scores,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


# ── FEEDBACK ──────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackResponse)
async def add_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(_optional_user_id),
):
    """
    ⭐ Ajouter un feedback sur une conversation (1 à 5 étoiles).

    Le feedback est lié à la conversation et optionnellement à l'utilisateur
    authentifié (token Bearer dans le header Authorization).
    """
    try:
        service = ChatbotService(db)
        return service.add_feedback(request, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("❌ Erreur feedback: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
