# 🚀 Grants Platform — Backend

> Plateforme autonome de soumission de grants pour startups early-stage, propulsée par des AI Agents.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![LLM](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3-orange)
![License](https://img.shields.io/badge/License-MIT-purple)
![PFE](https://img.shields.io/badge/PFE-2025-red)

---

## 📌 Description

Ce backend est le cœur de la plateforme. Il orchestre l'ensemble du pipeline IA :
extraction des données d'un pitch deck, recherche autonome de grants, adaptation du contenu et soumission automatique via Browser Agent.

---

## 🏗️ Architecture

```
backend/
├── main.py                  # Point d'entrée FastAPI
├── routers/
│   ├── pitch.py             # POST /api/v1/pitch/upload
│   ├── grants.py            # POST /api/v1/grants/search
│   └── submissions.py       # POST /api/v1/submissions/
├── services/
│   ├── extractor.py         # LLM extraction PDF/PPTX → JSON
│   ├── embedder.py          # ChromaDB embeddings (Mois 2)
│   ├── grant_finder.py      # Tavily web search (Mois 3)
│   └── content_adapter.py   # Adaptation contenu (Mois 3)
├── agents/
│   ├── orchestrator.py      # LangGraph state machine (Mois 2)
│   ├── search_agent.py      # Agent recherche grants (Mois 3)
│   └── browser_agent.py     # Browser-use + Playwright (Mois 4)
├── models/
│   ├── pitch.py             # Pydantic schemas pitch deck
│   ├── grant.py             # Pydantic schemas grant
│   └── submission.py        # Pydantic schemas soumission
├── core/
│   ├── config.py            # Configuration centralisée
│   ├── database.py          # PostgreSQL
│   ├── chromadb.py          # Vector store
│   └── redis.py             # Cache & queue
└── utils/
    ├── pdf_parser.py        # PyMuPDF extraction
    └── pptx_parser.py       # python-pptx extraction
```

---

## ⚡ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Framework | FastAPI + Uvicorn |
| LLM | Groq — LLaMA 3.3 70B (gratuit) |
| Extraction PDF | PyMuPDF |
| Extraction PPTX | python-pptx |
| Vector Store | ChromaDB |
| AI Agent | LangGraph + LangChain |
| Browser Agent | Browser-use + Playwright |
| Web Search | Tavily API |
| Database | PostgreSQL |
| Cache/Queue | Redis + Celery |
| Auth | JWT (python-jose) |

---

## 🚀 Démarrage rapide

### Prérequis
- Python 3.11+
- Clé API Groq (gratuit sur [console.groq.com](https://console.groq.com))

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/bahahajmabrouk/grants-platform-backend.git
cd grants-platform-backend

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate   # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env et ajouter ta clé GROQ_API_KEY

# 5. Lancer le serveur
uvicorn main:app --reload --port 8000
```

### Accès
| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI — tester l'API |
| http://localhost:8000/health | Health check |

---


## 🔑 Variables d'environnement

```env
# LLM
GROQ_API_KEY=gsk_...           # Requis — gratuit sur console.groq.com

# Optionnel
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Database (pour Docker)
DATABASE_URL=postgresql://postgres:postgres@db:5432/grants_db
REDIS_URL=redis://redis:6379/0
```

---

## 🎓 Contexte Académique

Ce projet est développé dans le cadre d'un **PFE (Projet de Fin d'Études) 2025**.

**Sujet** : Conception et développement d'une plateforme autonome de soumission de grants pour startups early-stage basée sur des AI Agents.

**Technologies clés étudiées** : LLM, RAG, AI Agents, LangGraph, Browser Automation.

---

## 👤 Auteur

**Baha HajMabrouk**
[![GitHub](https://img.shields.io/badge/GitHub-bahahajmabrouk-black?logo=github)](https://github.com/bahahajmabrouk)
