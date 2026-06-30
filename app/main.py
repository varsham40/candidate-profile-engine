import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routes import router

app = FastAPI(
    title="Candidate Profile Engine",
    version="1.0"
)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(router)
