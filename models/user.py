from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Database Model (SQLAlchemy) ────────────────────────

class UserDB(BaseModel):
    """Modèle User pour la base de données"""
    id: int
    email: str
    hashed_password: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Pydantic Schemas (API I/O) ─────────────────────────

class UserRegister(BaseModel):
    """Schéma d'inscription"""
    email: EmailStr
    password: str  # min 8 chars, 1 uppercase, 1 number
    first_name: str
    last_name: str
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schéma de connexion"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Réponse utilisateur (pas de password!)"""
    id: int
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Réponse après login/register"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int  # secondes


class TokenRefresh(BaseModel):
    """Requête de rafraîchissement"""
    refresh_token: str


class TokenData(BaseModel):
    """Données décodées du JWT"""
    user_id: int
    email: str
    iat: int  # issued at
    exp: int  # expiration


class ChangePassword(BaseModel):
    """Changement de password"""
    current_password: str
    new_password: str