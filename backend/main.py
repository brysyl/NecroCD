import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.supabase_client import get_store
from routers import exorcism, graves, telemetry

@asynccontextmanager
async def lifespan(_: FastAPI):
    store = get_store()
    logging.getLogger("necrocd").info("Supabase persistence %s", "enabled" if store.enabled else "disabled")
    yield


app = FastAPI(title="NecroCD", version="0.1.0", lifespan=lifespan)
origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(graves.router)
app.include_router(exorcism.router)
app.include_router(telemetry.router)


@app.get("/health")
async def health():
    return {"status": "alive", "message": "The dead walk.", "persistence": get_store().enabled}
