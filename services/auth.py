import jwt
import logging
from datetime import datetime, timedelta
from passlib.context import CryptContext
from core.config import settings

logger = logging.getLogger(__name__)

# ── Password Hashing ──────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hasher un password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un password"""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Management ──────────────────────────────

def create_access_token(user_id: int, email: str, expires_delta: timedelta = None) -> str:
    """Créer un access token JWT (15 min)"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": expire,
        "type": "access"
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.info(f"✅ Access token créé pour user {user_id}")
    return token


def create_refresh_token(user_id: int, email: str, expires_delta: timedelta = None) -> str:
    """Créer un refresh token JWT (7 jours)"""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": expire,
        "type": "refresh"
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.info(f"✅ Refresh token créé pour user {user_id}")
    return token


def decode_token(token: str) -> dict:
    """Décoder et valider un JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("❌ Token expiré")
        raise ValueError("Token expiré")
    except jwt.InvalidTokenError:
        logger.error("❌ Token invalide")
        raise ValueError("Token invalide")


def verify_token(token: str) -> int:
    """Vérifier un token et retourner l'user_id"""
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise ValueError("user_id manquant dans le token")
        
        return user_id
    except Exception as e:
        logger.error(f"❌ Erreur vérification token: {str(e)}")
        raise