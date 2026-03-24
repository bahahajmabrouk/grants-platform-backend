import uuid
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from core.config import settings
from services.extractor import extract_pitch_data
from models.pitch import PitchUploadResponse, PitchExtractedData

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
    except Exception as e:
        pitch_store[pitch_id]["status"] = "failed"
        pitch_store[pitch_id]["error"] = str(e)


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
                if p.get("extracted_data") else "—"
        }
        for p in pitch_store.values()
    ]
