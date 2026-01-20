from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Use an environment variable for the DB URL, defaulting to SQLite for local testing if not set
# For production PostgreSQL: postgresql://user:password@localhost/dbname
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./workflow.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # specific args for sqlite to handle threads if needed, ignored by postgres
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
