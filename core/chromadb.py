import chromadb
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Créer le dossier s'il n'existe pas
CHROMA_PATH = Path("./chroma_data")
CHROMA_PATH.mkdir(exist_ok=True)

try:
    # Client ChromaDB persistant (mode local)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    logger.info(f"✅ ChromaDB client initialized at {CHROMA_PATH}")
except Exception as e:
    logger.error(f"❌ Erreur initialisation ChromaDB: {str(e)}")
    raise

# ── Collections ────────────────────────────────────────

# Collection pour les pitches
try:
    collection = chroma_client.get_or_create_collection(
        name="pitches",
        metadata={"hnsw:space": "cosine"}
    )
    logger.info("✅ ChromaDB collection 'pitches' ready")
except Exception as e:
    logger.error(f"❌ Erreur création collection pitches: {str(e)}")
    raise

# Collection pour les grants (future usage)
try:
    grants_collection = chroma_client.get_or_create_collection(
        name="grants",
        metadata={"hnsw:space": "cosine"}
    )
    logger.info("✅ ChromaDB collection 'grants' ready")
except Exception as e:
    logger.error(f"❌ Erreur création collection grants: {str(e)}")
    raise