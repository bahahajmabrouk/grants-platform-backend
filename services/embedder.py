from sentence_transformers import SentenceTransformer
from core.chromadb import collection
from models.pitch import PitchExtractedData
import logging

logger = logging.getLogger(__name__)

# ── Model Loading ──────────────────────────────────────
# Charger le modèle une seule fois (cache - pas de rechargement)
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("✅ SentenceTransformer model loaded: all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"❌ Erreur chargement SentenceTransformer: {str(e)}")
    raise


# ── Utility Functions ──────────────────────────────────

def create_pitch_embedding_text(data: PitchExtractedData) -> str:
    """
    Combine tous les champs textuels pour créer l'embedding
    Plus le texte est riche, meilleure est la représentation vectorielle
    """
    text_parts = [
        data.startup_name or "",
        data.problem or "",
        data.solution or "",
        data.industry or "",
        data.stage or "",
        data.country or "",
        data.business_model or "",
        data.market_size or "",
        " ".join(data.keywords) if data.keywords else "",
    ]
    # Filtrer les chaînes vides et joindre
    return " ".join([part for part in text_parts if part])


# ── Main Embedding Functions ───────────────────────────

def embed_and_store_pitch(
    pitch_id: str,
    extracted_data: PitchExtractedData
) -> dict:
    """
    Embedde les données du pitch et les stocke dans ChromaDB
    
    Args:
        pitch_id (str): UUID unique du pitch
        extracted_data (PitchExtractedData): Données extraites du pitch deck
        
    Returns:
        dict: {
            "status": "success" | "error",
            "pitch_id": str,
            "message": str,
            "embedding_dim": int (384),
            "error": str | None
        }
    """
    try:
        # 1. Créer le texte pour embedding
        text = create_pitch_embedding_text(extracted_data)
        
        if not text.strip():
            raise ValueError("Aucun texte disponible pour embedding")
        
        logger.info(f"🔄 Embedding pitch {pitch_id}... (text length: {len(text)})")
        
        # 2. Générer l'embedding (384 dimensions)
        embedding = model.encode(text).tolist()
        embedding_dim = len(embedding)
        
        # 3. Préparer les métadonnées
        metadata = {
            "startup_name": extracted_data.startup_name,
            "industry": extracted_data.industry,
            "stage": extracted_data.stage,
            "country": extracted_data.country,
            "business_model": extracted_data.business_model,
            "keywords": ",".join(extracted_data.keywords) if extracted_data.keywords else "",
        }
        
        # 4. Ajouter à ChromaDB
        collection.add(
            ids=[pitch_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[text]  # Optionnel, pour la traçabilité
        )
        
        logger.info(f"✅ Pitch {pitch_id} embedé avec succès ({embedding_dim}D)")
        
        return {
            "status": "success",
            "pitch_id": pitch_id,
            "message": f"Embedding stocké dans ChromaDB ({embedding_dim} dimensions)",
            "embedding_dim": embedding_dim,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur embedding pitch {pitch_id}: {str(e)}")
        return {
            "status": "error",
            "pitch_id": pitch_id,
            "message": "",
            "embedding_dim": 0,
            "error": str(e)
        }


def search_similar_pitches(
    query: str,
    n_results: int = 5,
    filters: dict = None
) -> dict:
    """
    Recherche des pitches similaires par requête texte
    
    Args:
        query (str): Texte de recherche
        n_results (int): Nombre de résultats à retourner (1-100, défaut 5)
        filters (dict): Filtres optionnels 
                       ex: {"industry": "FinTech", "stage": "Seed"}
        
    Returns:
        dict: {
            "status": "success" | "error",
            "query": str,
            "results_count": int,
            "results": [
                {
                    "pitch_id": str,
                    "similarity_score": float (0-1),
                    "startup_name": str,
                    "industry": str,
                    "stage": str,
                    "country": str,
                },
                ...
            ],
            "error": str | None
        }
    """
    try:
        logger.info(f"🔍 Recherche en cours: '{query}' (top {n_results})")
        
        # 1. Embedder la requête
        query_embedding = model.encode(query).tolist()
        
        # 2. Construire les filtres ChromaDB
        where = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append({key: {"$eq": value}})
            if len(conditions) == 1:
                where = conditions[0]
            elif len(conditions) > 1:
                where = {"$and": conditions}
            logger.info(f"   Filtres appliqués: {filters}")
        
        # 3. Chercher dans ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, 100),
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # 4. Formater les résultats
        formatted_results = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, pitch_id in enumerate(results["ids"][0]):
                # Convertir distance en similarité (distance cosine: 0-2, où 0=identique)
                distance = results["distances"][0][i]
                similarity = 1 - (distance / 2)  # Normaliser à 0-1
                similarity = max(0, min(1, similarity))  # Clamp à [0,1]
                
                formatted_results.append({
                    "pitch_id": pitch_id,
                    "similarity_score": round(similarity, 3),
                    "startup_name": results["metadatas"][0][i].get("startup_name", "N/A"),
                    "industry": results["metadatas"][0][i].get("industry", "N/A"),
                    "stage": results["metadatas"][0][i].get("stage", "N/A"),
                    "country": results["metadatas"][0][i].get("country", "N/A"),
                })
        
        logger.info(f"✅ Recherche terminée: {len(formatted_results)} résultats trouvés")
        
        return {
            "status": "success",
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur recherche: {str(e)}")
        return {
            "status": "error",
            "query": query,
            "results_count": 0,
            "results": [],
            "error": str(e)
        }


def delete_pitch_embedding(pitch_id: str) -> dict:
    """
    Supprimer un pitch de la collection ChromaDB
    
    Args:
        pitch_id (str): UUID du pitch à supprimer
        
    Returns:
        dict: {"status": "success" | "error", "pitch_id": str, "error": str | None}
    """
    try:
        collection.delete(ids=[pitch_id])
        logger.info(f"✅ Pitch {pitch_id} supprimé de ChromaDB")
        return {
            "status": "success",
            "pitch_id": pitch_id,
            "error": None
        }
    except Exception as e:
        logger.error(f"❌ Erreur suppression embedding {pitch_id}: {str(e)}")
        return {
            "status": "error",
            "pitch_id": pitch_id,
            "error": str(e)
        }


def get_collection_stats() -> dict:
    """
    Obtenir les statistiques de la collection
    
    Returns:
        dict: {"total_embeddings": int, "collection_name": str}
    """
    try:
        count = collection.count()
        logger.info(f"📊 Collection stats: {count} embeddings")
        return {
            "status": "success",
            "total_embeddings": count,
            "collection_name": "pitches",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dim": 384,
        }
    except Exception as e:
        logger.error(f"❌ Erreur stats collection: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }