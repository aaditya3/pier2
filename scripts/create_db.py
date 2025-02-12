import yaml
from sqlalchemy import create_engine
from pier2.models import Base

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

DATABASE_URL = config["database"]["url"]

try:
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind = engine)
    print("Database tables created successfully!")
except Exception as e:
    print(f"Error creating database tables: {e}")


