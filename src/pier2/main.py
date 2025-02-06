from fastapi import FastAPI
import logging, logging.config
import sys
from configparser import ConfigParser
from .routers import customers

def setup_logging():
    logging.config.fileConfig('logging_config.ini')

# setup_logging()
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.info("Logging has been setup.")

app = FastAPI()
app.include_router(customers.router)

logger.info("Routers have been added.")


@app.get("/")
async def root():
    return {"message": "All you touch and all you see is all your life will ever be."}