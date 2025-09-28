import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .service import InsightEngine

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = Settings()
engine = InsightEngine(settings)


@asynccontextmanager
def lifespan(_: FastAPI):
    await asyncio.to_thread(engine.start)
    try:
        yield
    finally:
        await asyncio.to_thread(engine.stop)


app = FastAPI(
    title="Siap Suhu LLM Insight Service",
    description="Layanan analisis telemetry + insight berbasis LLM",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
