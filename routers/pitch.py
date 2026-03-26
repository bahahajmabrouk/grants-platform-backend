import uuid
import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from core.config import settings
from services.extractor import extract_pitch_data
from models.pitch import (
    PitchUploadResponse, 
    PitchExtractedData, 
    PitchEmbeddingResponse, 
    SearchResponse
)

# ── Logger Setup ───────────────────────────────────────
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pitch", tags=["Pitch Deck"])

# Stockage temporaire en mémoire (à remplacer par PostgreSQL en Mois 2)
pitch_store: dict[str, dict] = {}

ALLOWED_EXTENSIONS = {"pdf", "pptx", "ppt"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/upload", response_model=PitchUploadResponse)
async def upload_pitch_deck(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF ou PPTX du pitch deck")
):
    """
    📄 Upload un pitch deck et lance l'extraction des données.
    
    - Accepte PDF et PPTX
    - Extrait automatiquement : nom, industrie, problème, solution, marché...
    - Retourne immédiatement avec status='processing', 
      puis met à jour quand l'extraction est terminée
    """
    # Validation du fichier
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Utilisez PDF ou PPTX."
        )

    # Vérification taille
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop grand ({size_mb:.1f}MB). Maximum: {settings.max_file_size_mb}MB"
        )

    # Génération d'un ID unique
    pitch_id = str(uuid.uuid4())

    # Sauvegarde du fichier
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_ext = file.filename.rsplit(".", 1)[1].lower()
    file_path = f"{settings.upload_dir}/{pitch_id}.{file_ext}"

    with open(file_path, "wb") as f:
        f.write(content)

    # Stockage initial
    pitch_store[pitch_id] = {
        "pitch_id": pitch_id,
        "filename": file.filename,
        "file_path": file_path,
        "status": "processing",
        "extracted_data": None,
        "is_embedded": False,  # ✨ NEW
    }

    # Extraction en arrière-plan
    background_tasks.add_task(
        run_extraction,
        pitch_id=pitch_id,
        file_path=file_path,
        filename=file.filename
    )

    return PitchUploadResponse(
        pitch_id=pitch_id,
        filename=file.filename,
        status="processing",
        message="✅ Fichier reçu. Extraction en cours par le LLM..."
    )


def run_extraction(pitch_id: str, file_path: str, filename: str):
    """Tâche d'extraction lancée en arrière-plan"""
    try:
        extracted = extract_pitch_data(file_path, filename)
        pitch_store[pitch_id]["extracted_data"] = extracted
        pitch_store[pitch_id]["status"] = "completed"
        
        # ✨ NEW: Embedder automatiquement après extraction
        try:
            from services.embedder import embed_and_store_pitch
            embed_result = embed_and_store_pitch(pitch_id, extracted)
            pitch_store[pitch_id]["is_embedded"] = embed_result["status"] == "success"
            logger.info(f"✅ Pitch {pitch_id} embedé automatiquement")
        except Exception as e:
            logger.error(f"⚠️ Erreur embedding auto pour {pitch_id}: {str(e)}")
            pitch_store[pitch_id]["is_embedded"] = False
            
    except Exception as e:
        pitch_store[pitch_id]["status"] = "failed"
        pitch_store[pitch_id]["error"] = str(e)
        logger.error(f"❌ Erreur extraction pitch {pitch_id}: {str(e)}")


@router.get("/{pitch_id}", response_model=PitchUploadResponse)
async def get_pitch_status(pitch_id: str):
    """
    📊 Récupère le statut et les données d'un pitch deck uploadé.
    Appeler toutes les 2s depuis le frontend pour polling.
    """
    if pitch_id not in pitch_store:
        raise HTTPException(status_code=404, detail="Pitch deck introuvable")

    pitch = pitch_store[pitch_id]
    return PitchUploadResponse(
        pitch_id=pitch_id,
        filename=pitch["filename"],
        status=pitch["status"],
        extracted_data=pitch.get("extracted_data"),
        message="Extraction terminée ✅" if pitch["status"] == "completed" else
                pitch.get("error", "Traitement en cours...")
    )


@router.get("/", response_model=list[dict])
async def list_pitches():
    """📋 Liste tous les pitch decks uploadés"""
    return [
        {
            "pitch_id": p["pitch_id"],
            "filename": p["filename"],
            "status": p["status"],
            "startup_name": p["extracted_data"].startup_name
                if p.get("extracted_data") else "—",
            "is_embedded": p.get("is_embedded", False),  # ✨ NEW
        }
        for p in pitch_store.values()
    ]


# ── EMBEDDING & SEARCH ENDPOINTS ──────────────────────────────────────────────

@router.post("/{pitch_id}/embed", response_model=PitchEmbeddingResponse)
async def embed_pitch(pitch_id: str):
    """
    💾 Embedde les données extraites d'un pitch dans ChromaDB
    
    - Appeler APRÈS l'extraction (status='completed')
    - Convertit le texte en vecteurs 384D
    - Stocke dans ChromaDB pour recherche rapide
    
    Example:
        POST /api/v1/pitch/{pitch_id}/embed
    """
    if pitch_id not in pitch_store:
        raise HTTPException(status_code=404, detail="Pitch deck introuvable")
    
    pitch = pitch_store[pitch_id]
    
    # Vérifier que l'extraction est complétée
    if pitch["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Pitch pas encore extrait. Status: {pitch['status']}"
        )
    
    if not pitch.get("extracted_data"):
        raise HTTPException(status_code=400, detail="Données extraites manquantes")
    
    # Embedder et stocker
    try:
        from services.embedder import embed_and_store_pitch
        result = embed_and_store_pitch(pitch_id, pitch["extracted_data"])
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'import embedder: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur embedding service")
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Marquer comme embedé
    pitch["is_embedded"] = True
    logger.info(f"✅ Pitch {pitch_id} embedé manuellement")
    
    return PitchEmbeddingResponse(**result)


@router.post("/search/similar", response_model=SearchResponse)
async def search_similar_pitches(
    query: str = Query(..., min_length=2, description="Texte de recherche"),
    n_results: int = Query(5, ge=1, le=100, description="Nombre de résultats"),
    industry: str = Query(None, description="Filtrer par industrie (ex: FinTech)"),
    stage: str = Query(None, description="Filtrer par stage (ex: Seed)"),
):
    """
    🔍 Recherche des pitches similaires par requête textuelle
    
    - Utilise les embeddings stockés dans ChromaDB
    - Retourne les N résultats les plus similaires
    - Supporte les filtres par industrie et stage
    
    Examples:
        POST /api/v1/pitch/search/similar?query=travel+accommodation&n_results=5
        POST /api/v1/pitch/search/similar?query=fintech&industry=FinTech&stage=Seed
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Query doit avoir au moins 2 caractères"
        )
    
    # Construire les filtres
    filters = {}
    if industry:
        filters["industry"] = industry
    if stage:
        filters["stage"] = stage
    
    try:
        from services.embedder import search_similar_pitches
        result = search_similar_pitches(query, n_results, filters if filters else None)
    except Exception as e:
        logger.error(f"❌ Erreur recherche: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur service recherche")
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    logger.info(f"🔍 Recherche '{query}' → {result['results_count']} résultats")
    
    return SearchResponse(**result)


@router.delete("/{pitch_id}/remove-embedding")
async def remove_pitch_embedding(pitch_id: str):
    """
    🗑️ Supprime l'embedding d'un pitch de ChromaDB
    """
    try:
        from services.embedder import delete_pitch_embedding
        result = delete_pitch_embedding(pitch_id)
    except Exception as e:
        logger.error(f"❌ Erreur suppression embedding: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur suppression")
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    if pitch_id in pitch_store:
        pitch_store[pitch_id]["is_embedded"] = False
    
    logger.info(f"🗑️ Embedding supprimé pour {pitch_id}")
    
    return result