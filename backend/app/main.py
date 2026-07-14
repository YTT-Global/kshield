import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db, close_db
from app.api.v1.scan import router as api_v1_router
from app.api.v1.history import router as history_router
from app.api.v1.actions import router as actions_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("kshield")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing system modules and database engine...")
    await init_db()
    yield
    logger.info("Shutting down database connection pools safely...")
    await close_db()

app = FastAPI(
    title="KShield Engine",
    version="1.0.0",
    description="Local-first engine to detect code mutations, hallucinations, and security flaws.",
    lifespan=lifespan
)

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "kshield_backend"}
