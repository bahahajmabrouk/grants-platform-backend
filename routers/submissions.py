from fastapi import APIRouter

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.get("/")
async def list_submissions():
    """📤 À implémenter en Mois 4 — Soumission autonome via Browser Agent"""
    return {"message": "Browser Agent coming in Month 4 🚧", "submissions": []}
