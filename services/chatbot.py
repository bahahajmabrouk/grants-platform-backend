"""
Service chatbot avec intégration Ollama (llama3.2:1b).

Fonctionnalités :
- Évaluation de pitch sur 6 critères
- Chat interactif avec historique
- Génération de recommandations
- Gestion des conversations et feedback
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from core.database import (
    ChatbotConversationModel,
    ChatbotFeedbackModel,
    PitchModel,
)
from schemas.chatbot_schemas import (
    ChatRequest,
    ChatResponse,
    EvaluatePitchRequest,
    EvaluatePitchResponse,
    EvaluationCriteria,
    FeedbackRequest,
    FeedbackResponse,
)

logger = logging.getLogger(__name__)

# ── Ollama Configuration ───────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:1b"
OLLAMA_TIMEOUT = 120.0  # seconds

# ── Evaluation Criteria ────────────────────────────────

EVALUATION_CRITERIA_LABELS = [
    "Clarté du marché et opportunité",
    "Adéquation problème/solution",
    "Expérience et expertise de l'équipe",
    "Avantage concurrentiel",
    "Traction et métriques",
    "Clarté des besoins de financement",
]

EVALUATION_PROMPT_TEMPLATE = """Tu es un expert en évaluation de startups et de levées de fonds.

Évalue ce pitch deck sur 6 critères, chacun noté de 0 à 10.

PITCH:
Startup: {startup_name}
Industrie: {industry}
Stage: {stage}
Pays: {country}
Problème: {problem}
Solution: {solution}
Marché: {market_size}
Business Model: {business_model}
Équipe: {team}
Traction: {traction}
Financement recherché: {funding_needed}

CRITÈRES D'ÉVALUATION:
1. Clarté du marché et opportunité
2. Adéquation problème/solution
3. Expérience et expertise de l'équipe
4. Avantage concurrentiel
5. Traction et métriques
6. Clarté des besoins de financement

Réponds UNIQUEMENT en JSON valide avec ce format exact (sans markdown, sans explication) :
{{
  "criteria": [
    {{"criterion": "Clarté du marché et opportunité", "score": 7.5, "feedback": "..."}},
    {{"criterion": "Adéquation problème/solution", "score": 8.0, "feedback": "..."}},
    {{"criterion": "Expérience et expertise de l'équipe", "score": 6.0, "feedback": "..."}},
    {{"criterion": "Avantage concurrentiel", "score": 7.0, "feedback": "..."}},
    {{"criterion": "Traction et métriques", "score": 5.5, "feedback": "..."}},
    {{"criterion": "Clarté des besoins de financement", "score": 7.0, "feedback": "..."}}
  ],
  "recommendations": [
    "Recommandation actionnable 1",
    "Recommandation actionnable 2",
    "Recommandation actionnable 3"
  ],
  "summary": "Résumé global en 2-3 phrases."
}}"""


class ChatbotService:
    """
    Service principal du chatbot — évaluation Ollama + gestion des conversations.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Private: Ollama ────────────────────────────────

    async def _call_ollama(self, messages: List[Dict[str, str]]) -> str:
        """
        Appel asynchrone à l'API Ollama.

        Args:
            messages: Liste de messages au format {role, content}

        Returns:
            Texte de réponse du modèle

        Raises:
            Exception: Si Ollama est indisponible ou retourne une erreur
        """
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": messages,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

        except httpx.ConnectError:
            logger.error("❌ Impossible de connecter à Ollama sur %s", OLLAMA_BASE_URL)
            raise Exception(
                "Service Ollama indisponible. Assurez-vous qu'Ollama est démarré "
                f"sur {OLLAMA_BASE_URL} avec le modèle {OLLAMA_MODEL}."
            )
        except httpx.HTTPStatusError as exc:
            logger.error("❌ Erreur HTTP Ollama: %s", exc)
            raise Exception(f"Erreur Ollama: {exc.response.status_code}")
        except Exception as exc:
            logger.error("❌ Erreur appel Ollama: %s", exc)
            raise

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        Extrait le premier objet JSON valide d'un texte.

        Args:
            text: Texte potentiellement contenant du JSON

        Returns:
            Dictionnaire Python parsé

        Raises:
            ValueError: Si aucun JSON valide n'est trouvé ou si le texte est trop grand
        """
        # Guard against oversized responses (max 64 KB)
        if len(text) > 65_536:
            raise ValueError(
                "La réponse Ollama dépasse la taille maximale autorisée (64 KB)."
            )

        # Remove markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", text).strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object via regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError("Aucun JSON valide trouvé dans la réponse Ollama.")

    # ── Public: Evaluate ───────────────────────────────

    async def evaluate_pitch(
        self, request: EvaluatePitchRequest
    ) -> EvaluatePitchResponse:
        """
        Évalue un pitch deck sur 6 critères via Ollama.

        Args:
            request: EvaluatePitchRequest avec pitch_id

        Returns:
            EvaluatePitchResponse avec scores, recommandations et résumé

        Raises:
            ValueError: Si le pitch n'existe pas
            Exception: Si Ollama retourne une erreur
        """
        pitch = self.db.query(PitchModel).filter(
            PitchModel.pitch_id == request.pitch_id
        ).first()

        if not pitch:
            raise ValueError(f"Pitch '{request.pitch_id}' introuvable.")

        logger.info("🤖 Évaluation pitch %s — %s", request.pitch_id, pitch.startup_name)

        prompt = EVALUATION_PROMPT_TEMPLATE.format(
            startup_name=pitch.startup_name or "N/A",
            industry=pitch.industry or "N/A",
            stage=pitch.stage or "N/A",
            country=pitch.country or "N/A",
            problem=pitch.problem or "N/A",
            solution=pitch.solution or "N/A",
            market_size=pitch.market_size or "N/A",
            business_model=pitch.business_model or "N/A",
            team=pitch.team or "N/A",
            traction=pitch.traction or "Non mentionnée",
            funding_needed=pitch.funding_needed or "Non spécifié",
        )

        messages = [{"role": "user", "content": prompt}]
        response_text = await self._call_ollama(messages)

        eval_data = self._extract_json(response_text)

        criteria = [
            EvaluationCriteria(**c) for c in eval_data.get("criteria", [])
        ]

        overall_score = (
            sum(c.score for c in criteria) / len(criteria) if criteria else 0.0
        )

        conversation_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()

        evaluation_scores: Dict[str, Any] = {
            "overall": round(overall_score, 2),
            "criteria": [
                {"criterion": c.criterion, "score": c.score} for c in criteria
            ],
        }

        initial_messages = [
            {
                "role": "system",
                "content": (
                    f"Tu es un assistant expert pour la startup {pitch.startup_name}. "
                    "Tu as analysé leur pitch deck et tu peux répondre à leurs questions."
                ),
                "timestamp": now_iso,
            },
            {
                "role": "assistant",
                "content": (
                    f"J'ai évalué votre pitch. Score global : {overall_score:.1f}/10. "
                    "N'hésitez pas à me poser des questions sur votre évaluation."
                ),
                "timestamp": now_iso,
            },
        ]

        conversation = ChatbotConversationModel(
            conversation_id=conversation_id,
            pitch_id=request.pitch_id,
            messages=initial_messages,
            evaluation_scores=evaluation_scores,
        )
        self.db.add(conversation)
        self.db.commit()

        logger.info(
            "✅ Évaluation terminée — conversation %s, score %.1f/10",
            conversation_id,
            overall_score,
        )

        return EvaluatePitchResponse(
            conversation_id=conversation_id,
            pitch_id=request.pitch_id,
            overall_score=round(overall_score, 2),
            criteria=criteria,
            recommendations=eval_data.get("recommendations", []),
            summary=eval_data.get("summary", ""),
        )

    # ── Public: Chat ───────────────────────────────────

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Envoie un message et retourne la réponse du chatbot.

        La conversation est créée si elle n'existe pas encore.
        L'historique est persisté en base de données.

        Args:
            request: ChatRequest avec message, conversation_id optionnel et pitch_id

        Returns:
            ChatResponse avec la réponse du modèle
        """
        conversation = None
        if request.conversation_id:
            conversation = self.db.query(ChatbotConversationModel).filter(
                ChatbotConversationModel.conversation_id == request.conversation_id
            ).first()

        if not conversation:
            conversation_id = str(uuid.uuid4())
            conversation = ChatbotConversationModel(
                conversation_id=conversation_id,
                pitch_id=request.pitch_id,
                messages=[],
                evaluation_scores=None,
            )
            self.db.add(conversation)
            self.db.flush()

        history: List[Dict[str, Any]] = conversation.messages or []

        # Build Ollama message list
        ollama_messages: List[Dict[str, str]] = []

        # Add system context if linked to a pitch
        if conversation.pitch_id:
            pitch = self.db.query(PitchModel).filter(
                PitchModel.pitch_id == conversation.pitch_id
            ).first()
            if pitch:
                ollama_messages.append({
                    "role": "system",
                    "content": (
                        f"Tu es un assistant expert pour la startup {pitch.startup_name} "
                        f"dans le secteur {pitch.industry or 'inconnu'}. "
                        "Réponds de manière concise et actionnable."
                    ),
                })

        # Replay conversation history (skip system messages already injected)
        for msg in history:
            if msg.get("role") in ("user", "assistant"):
                ollama_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Append current user message
        ollama_messages.append({"role": "user", "content": request.message})

        response_text = await self._call_ollama(ollama_messages)

        now_iso = datetime.utcnow().isoformat()
        updated_messages = list(history) + [
            {"role": "user", "content": request.message, "timestamp": now_iso},
            {"role": "assistant", "content": response_text, "timestamp": now_iso},
        ]

        conversation.messages = updated_messages
        self.db.commit()

        logger.info("✅ Chat — conversation %s", conversation.conversation_id)

        return ChatResponse(
            conversation_id=conversation.conversation_id,
            message=response_text,
            role="assistant",
            timestamp=datetime.utcnow(),
        )

    # ── Public: Conversation history ───────────────────

    def get_conversation(
        self, conversation_id: str
    ) -> Optional[ChatbotConversationModel]:
        """
        Récupère une conversation par son identifiant.

        Args:
            conversation_id: UUID de la conversation

        Returns:
            ChatbotConversationModel ou None
        """
        return self.db.query(ChatbotConversationModel).filter(
            ChatbotConversationModel.conversation_id == conversation_id
        ).first()

    # ── Public: Feedback ───────────────────────────────

    def add_feedback(
        self,
        request: FeedbackRequest,
        user_id: Optional[int] = None,
    ) -> FeedbackResponse:
        """
        Enregistre le feedback utilisateur pour une conversation.

        Args:
            request: FeedbackRequest avec conversation_id, rating et comment
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            FeedbackResponse avec l'ID du feedback créé

        Raises:
            ValueError: Si la conversation n'existe pas
        """
        conversation = self.db.query(ChatbotConversationModel).filter(
            ChatbotConversationModel.conversation_id == request.conversation_id
        ).first()

        if not conversation:
            raise ValueError(
                f"Conversation '{request.conversation_id}' introuvable."
            )

        feedback = ChatbotFeedbackModel(
            conversation_id=request.conversation_id,
            user_id=user_id,
            rating=request.rating,
            comment=request.comment,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        logger.info(
            "✅ Feedback %d/5 enregistré — conversation %s",
            request.rating,
            request.conversation_id,
        )

        return FeedbackResponse(
            success=True,
            message="Feedback enregistré avec succès",
            feedback_id=feedback.id,
        )
