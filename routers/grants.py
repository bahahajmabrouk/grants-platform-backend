from fastapi import APIRouter

router = APIRouter(prefix="/grants", tags=["Grants"])


@router.get("/")
async def list_grants():
    """🔍 À implémenter en Mois 3 — Recherche autonome de grants"""
    return {"message": "Grant search coming in Month 3 🚧", "grants": []}
