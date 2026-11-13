import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import exorcism, graves, telemetry

app = FastAPI(title="NecroCD", version="0.1.0")
origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(graves.router)
app.include_router(exorcism.router)
app.include_router(telemetry.router)


@app.get("/health")
async def health():
    return {"status": "alive", "message": "The dead walk."}
