from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Falling back to SQLite for local development since PostgreSQL connection was refused
SQLALCHEMY_DATABASE_URL = "sqlite:///./gold_estimation.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
