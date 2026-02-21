"""REST API приложение на FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import datasets, health, models
from app.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    log.info("Запуск приложения...")
    yield
    log.info("Остановка приложения...")


app = FastAPI(
    title="ML Model Training API",
    description="API для обучения и инференса ML моделей",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["Datasets"])


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {
        "message": "ML Model Training API",
        "version": __version__,
        "docs": "/docs",
    }
