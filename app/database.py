from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

DATABASE_URL = settings.DATABASE_URL
SQL_ECHO = settings.SQL_ECHO

# SQLite (used for quick local dev without Postgres) needs this flag because
# FastAPI serves each request from a different thread.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=SQL_ECHO, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so they register with Base before create_all.
    from app.models import reading_orm  # noqa: F401
    Base.metadata.create_all(bind=engine)
