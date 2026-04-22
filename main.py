from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from core.config import settings
from core.database import create_tables                       
from routers import pitch, grants, submissions, search, auth, chatbot

# ── Logger Setup ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────
app = FastAPI(
    title="🚀 Grants Platform API",
    description="""
    Plateforme autonome de soumission de grants pour startups.
    
    ## Modules
    - **🔐 Auth** — Inscription, connexion, JWT tokens
    - **📄 Pitch** — Upload et extraction des données du pitch deck
    - **🔍 Grants** — Recherche autonome de grants et compétitions
    - **📤 Submissions** — Soumission autonome via Browser Agent
    - **🔎 Search** — Recherche sémantique d'embeddings
    - **🤖 Chatbot** — Évaluation de pitch et chat interactif avec Ollama
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

create_tables()                                                # ← ajouté

# ── CORS ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1")
app.include_router(pitch.router,        prefix="/api/v1")
app.include_router(search.router,       prefix="/api/v1")
app.include_router(grants.router,       prefix="/api/v1")
app.include_router(submissions.router,  prefix="/api/v1")
app.include_router(chatbot.router,      prefix="/api/v1")

# ── Uploads statiques ─────────────────────────────────
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Health check ──────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "version": "0.1.0"
    }

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "🚀 Grants Platform API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/api/v1/auth",
            "pitch": "/api/v1/pitch",
            "search": "/api/v1/search",
            "grants": "/api/v1/grants",
            "submissions": "/api/v1/submissions",
            "chatbot": "/api/v1/chatbot",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)