import logging
import yaml
from .models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import wraps
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

def transactional(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = kwargs['db']
        try:
            result = func(*args, **kwargs)
            db.commit()
            return result
        except HTTPException as e:
            db.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Transaction failed: {e}")
            raise HTTPException(status_code =
                                status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="An internal server error occurred")
            raise
    return wrapper

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

DATABASE_URL = config["database"]["url"]
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()