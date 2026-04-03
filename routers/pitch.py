import uuid
import os
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.config import settings
from core.database import get_db, PitchModel
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


# ── Request Models ─────────────────────────────────────

class SearchRequest(BaseModel):
    """Modèle pour la recherche de pitches similaires"""
    query: str
    n_results: int = 5
    industry: Optional[str] = None
    stage: Optional[str] = None
    country: Optional[str] = None


# ── Utility Functions ──────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── ENDPOINTS ──────────────────────────────────────────

@router.post("/upload", response_model=PitchUploadResponse)
async def upload_pitch_deck(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF ou PPTX du pitch deck"),
    db: Session = Depends(get_db)
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

    # Créer un enregistrement dans la base de données
    db_pitch = PitchModel(
        pitch_id=pitch_id,
        filename=file.filename,
        file_path=file_path,
        status="processing",
        extracted_data=None,
        is_embedded=False
    )
    db.add(db_pitch)
    db.commit()

    # Stockage initial en mémoire (fallback)
    pitch_store[pitch_id] = {
        "pitch_id": pitch_id,
        "filename": file.filename,
        "file_path": file_path,
        "status": "processing",
        "extracted_data": None,
        "is_embedded": False,
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
    from core.database import SessionLocal, PitchModel
    db = SessionLocal()
    
    try:
        extracted = extract_pitch_data(file_path, filename)
        pitch_store[pitch_id]["extracted_data"] = extracted
        pitch_store[pitch_id]["status"] = "completed"
        
        # Update database record
        db_pitch = db.query(PitchModel).filter(PitchModel.pitch_id == pitch_id).first()
        if db_pitch:
            db_pitch.status = "completed"
            db_pitch.extracted_data = extracted.dict() if hasattr(extracted, 'dict') else extracted
            db_pitch.startup_name = extracted.startup_name
            db_pitch.industry = extracted.industry
            db_pitch.stage = extracted.stage
            db_pitch.country = extracted.country
            db_pitch.problem = extracted.problem
            db_pitch.solution = extracted.solution
            db_pitch.market_size = extracted.market_size
            db_pitch.business_model = extracted.business_model
            db_pitch.team = extracted.team
            db_pitch.traction = extracted.traction
            db_pitch.funding_needed = extracted.funding_needed
            db_pitch.keywords = extracted.keywords
            db.commit()
        
        # ✨ NEW: Embedder automatiquement après extraction
        try:
            from services.embedder import embed_and_store_pitch
            embed_result = embed_and_store_pitch(pitch_id, extracted)
            pitch_store[pitch_id]["is_embedded"] = embed_result["status"] == "success"
            if db_pitch:
                db_pitch.is_embedded = embed_result["status"] == "success"
                db.commit()
            logger.info(f"✅ Pitch {pitch_id} embedé automatiquement")
        except Exception as e:
            logger.error(f"⚠️ Erreur embedding auto pour {pitch_id}: {str(e)}")
            pitch_store[pitch_id]["is_embedded"] = False
            
    except Exception as e:
        pitch_store[pitch_id]["status"] = "failed"
        pitch_store[pitch_id]["error"] = str(e)
        
        # Update database with error
        db_pitch = db.query(PitchModel).filter(PitchModel.pitch_id == pitch_id).first()
        if db_pitch:
            db_pitch.status = "failed"
            db_pitch.error_message = str(e)
            db.commit()
        
        logger.error(f"❌ Erreur extraction pitch {pitch_id}: {str(e)}")
    finally:
        db.close()


@router.get("/{pitch_id}", response_model=PitchUploadResponse)
async def get_pitch_status(pitch_id: str, db: Session = Depends(get_db)):
    """
    📊 Récupère le statut et les données d'un pitch deck uploadé.
    Appeler toutes les 2s depuis le frontend pour polling.
    """
    # Try database first
    db_pitch = db.query(PitchModel).filter(PitchModel.pitch_id == pitch_id).first()
    if db_pitch:
        extracted_data = None
        if db_pitch.extracted_data:
            extracted_data = PitchExtractedData(**db_pitch.extracted_data) if isinstance(db_pitch.extracted_data, dict) else db_pitch.extracted_data
        
        return PitchUploadResponse(
            pitch_id=pitch_id,
            filename=db_pitch.filename,
            status=db_pitch.status,
            extracted_data=extracted_data,
            message="Extraction terminée ✅" if db_pitch.status == "completed" 
                    else db_pitch.error_message or "Traitement en cours..."
        )
    
    # Fallback to memory store
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
async def list_pitches(db: Session = Depends(get_db)):
    """📋 Liste tous les pitch decks uploadés"""
    # Get from database
    db_pitches = db.query(PitchModel).order_by(PitchModel.created_at.desc()).all()
    
    results = []
    for p in db_pitches:
        results.append({
            "pitch_id": p.pitch_id,
            "filename": p.filename,
            "status": p.status,
            "startup_name": p.startup_name or "—",
            "is_embedded": p.is_embedded,
        })
    
    return results


# ── EMBEDDING & SEARCH ENDPOINTS ──────────────────────

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
async def search_similar_pitches(search: SearchRequest):
    """
    🔍 Recherche des pitches similaires par requête textuelle
    
    - Utilise les embeddings stockés dans ChromaDB
    - Retourne les N résultats les plus similaires
    - Supporte les filtres par industrie, stage et pays
    
    Example:
        POST /api/v1/pitch/search/similar
        {
            "query": "travel accommodation",
            "n_results": 5,
            "industry": "TravelTech",
            "stage": "Seed"
        }
    """
    query = search.query
    n_results = search.n_results
    industry = search.industry
    stage = search.stage
    country = search.country
    
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
    if country:
        filters["country"] = country
    
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