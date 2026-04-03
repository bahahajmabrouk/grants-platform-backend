import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from models.user import (
    UserRegister, UserLogin, UserResponse,
    TokenResponse, TokenRefresh, ChangePassword,
)
from services.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_token,
)
from core.database import get_db, UserModel
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Dependency JWT ─────────────────────────────────────

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> UserModel:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Schéma invalide")
        user_id = verify_token(token)
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token invalide: {str(e)}",
                            headers={"WWW-Authenticate": "Bearer"})


# ── REGISTER ──────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """📝 Créer un nouveau compte utilisateur"""

    # Email unique
    existing = db.query(UserModel).filter(
        UserModel.email == user_data.email.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")

    # Validation password
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password min 8 caractères")
    if not any(c.isupper() for c in user_data.password):
        raise HTTPException(status_code=400, detail="Password doit contenir une majuscule")
    if not any(c.isdigit() for c in user_data.password):
        raise HTTPException(status_code=400, detail="Password doit contenir un chiffre")

    # Créer l'utilisateur dans SQLite
    user = UserModel(
        email=user_data.email.lower(),
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        company_name=user_data.company_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token  = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    logger.info(f"✅ Nouvel utilisateur: {user.email} (ID: {user.id})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id, email=user.email,
            first_name=user.first_name, last_name=user.last_name,
            company_name=user.company_name, is_active=user.is_active,
            created_at=user.created_at,
        ),
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ── LOGIN ─────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """🔐 Se connecter avec email et password"""

    user = db.query(UserModel).filter(
        UserModel.email == credentials.email.lower()
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou password incorrect")

    access_token  = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    logger.info(f"✅ Login: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id, email=user.email,
            first_name=user.first_name, last_name=user.last_name,
            company_name=user.company_name, is_active=user.is_active,
            created_at=user.created_at,
        ),
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ── REFRESH ───────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """🔄 Rafraîchir l'access token"""
    try:
        user_id = verify_token(token_data.refresh_token)
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        access_token = create_access_token(user.id, user.email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=token_data.refresh_token,
            user=UserResponse(
                id=user.id, email=user.email,
                first_name=user.first_name, last_name=user.last_name,
                company_name=user.company_name, is_active=user.is_active,
                created_at=user.created_at,
            ),
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token invalide: {str(e)}")


# ── PROFILE ───────────────────────────────────────────

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: UserModel = Depends(get_current_user)):
    """👤 Profil de l'utilisateur connecté"""
    return UserResponse(
        id=current_user.id, email=current_user.email,
        first_name=current_user.first_name, last_name=current_user.last_name,
        company_name=current_user.company_name, is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ── CHANGE PASSWORD ───────────────────────────────────

@router.post("/change-password")
async def change_password(
    pwd_data: ChangePassword,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """🔑 Changer le password"""
    if not verify_password(pwd_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Password actuel incorrect")

    current_user.hashed_password = hash_password(pwd_data.new_password)
    db.commit()

    return {"status": "success", "message": "Password changé avec succès"}


# ── LOGOUT ────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user: UserModel = Depends(get_current_user)):
    """👋 Se déconnecter"""
    logger.info(f"✅ Logout: {current_user.email}")
    return {"status": "success", "message": "Déconnecté avec succès"}


# ── VALIDATE TOKEN ────────────────────────────────────

@router.get("/validate-token")
async def validate_token(current_user: UserModel = Depends(get_current_user)):
    """✅ Valider le token"""
    return {"status": "valid", "user_id": current_user.id, "email": current_user.email}