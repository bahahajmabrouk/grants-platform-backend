from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# SQLite — fichier local, pas besoin d'installation
DATABASE_URL = "sqlite:///./grants.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # nécessaire pour SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Table User ────────────────────────────────────────
class UserModel(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    email          = Column(String, unique=True, index=True, nullable=False)
    hashed_password= Column(String, nullable=False)
    first_name     = Column(String, nullable=False)
    last_name      = Column(String, nullable=False)
    company_name   = Column(String, nullable=True)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Table Pitch ────────────────────────────────────────
class PitchModel(Base):
    __tablename__ = "pitches"

    id                  = Column(Integer, primary_key=True, index=True)
    pitch_id            = Column(String, unique=True, index=True, nullable=False)
    user_id             = Column(Integer, nullable=True, index=True)  # Link to user (optional for now)
    filename            = Column(String, nullable=False)
    file_path           = Column(String, nullable=False)
    status              = Column(String, default="processing")  # processing | completed | failed
    extracted_data      = Column(JSON, nullable=True)  # Store full extracted data as JSON
    startup_name        = Column(String, nullable=True, index=True)
    industry            = Column(String, nullable=True)
    stage               = Column(String, nullable=True)
    country             = Column(String, nullable=True)
    problem             = Column(Text, nullable=True)
    solution            = Column(Text, nullable=True)
    market_size         = Column(Text, nullable=True)
    business_model      = Column(Text, nullable=True)
    team                = Column(Text, nullable=True)
    traction            = Column(Text, nullable=True)
    funding_needed      = Column(String, nullable=True)
    keywords            = Column(JSON, nullable=True)  # Store array of keywords
    is_embedded         = Column(Boolean, default=False)  # Track if embeddings were created
    error_message       = Column(Text, nullable=True)  # Store error details if status = failed
    created_at          = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def create_tables():
    """Créer toutes les tables si elles n'existent pas"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency FastAPI pour obtenir une session DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()