from fastapi import APIRouter, HTTPException, Query
from models.pitch import SearchResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/pitches", response_model=SearchResponse)
async def search_pitches_endpoint(
    query: str = Query(..., min_length=2, description="Texte de recherche"),
    n_results: int = Query(5, ge=1, le=100, description="Nombre de résultats"),
    industry: str = Query(None, description="Filtrer par industrie (ex: FinTech)"),
    stage: str = Query(None, description="Filtrer par stage (ex: Seed)"),
    country: str = Query(None, description="Filtrer par pays (ex: Tunisia)"),
):
    """
    🔍 Recherche tous les pitches par requête sémantique
    
    Utilise les embeddings ChromaDB pour trouver les startups similaires.
    Supporte les filtres par industrie, stage et pays.
    
    Exemples:
    - `/search/pitches?query=travel accommodation`
    - `/search/pitches?query=sharing economy&industry=TravelTech&n_results=10`
    - `/search/pitches?query=fintech payments&stage=Series A`
    - `/search/pitches?query=renewable energy&country=Tunisia&n_results=20`
    """
    if len(query.strip()) < 2:
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


@router.get("/stats")
async def get_search_stats():
    """
    📊 Statistiques de la collection ChromaDB
    
    Retourne le nombre total d'embeddings et les infos du modèle.
    """
    try:
        from services.embedder import get_collection_stats
        stats = get_collection_stats()
        
        if stats["status"] == "error":
            raise HTTPException(status_code=500, detail=stats.get("error"))
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur service stats")


@router.get("/health")
async def search_service_health():
    """
    🏥 Vérifier la santé du service de recherche
    
    Teste la connexion à ChromaDB et le modèle d'embedding.
    """
    try:
        from services.embedder import get_collection_stats
        stats = get_collection_stats()
        
        if stats["status"] == "error":
            return {
                "status": "unhealthy",
                "chroma_status": "❌ Down",
                "model_status": "❌ Error",
            }
        
        return {
            "status": "healthy",
            "chroma_status": "✅ Connected",
            "model_status": "✅ Loaded",
            "embeddings_count": stats["total_embeddings"],
            "embedding_model": stats["embedding_model"],
            "embedding_dim": stats["embedding_dim"],
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }