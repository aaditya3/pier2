import yaml
from .models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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