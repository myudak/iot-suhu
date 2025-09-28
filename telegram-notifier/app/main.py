import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .service import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = Settings()
notifier = TelegramNotifier(settings)


@asynccontextmanager
def lifespan(_: FastAPI):
    await notifier.start()
    try:
        yield
    finally:
        await notifier.stop()


app = FastAPI(
    title="Siap Suhu Telegram Notifier",
    description="Meneruskan insight ke Telegram",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
