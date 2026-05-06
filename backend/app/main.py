from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.cases import router as cases_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.directives import router as directives_router
from app.api.routes.upload import router as upload_router

# 🔥 ADD THESE IMPORTS
from app.database import engine
from app.models.base import Base

app = FastAPI(title="AadeshPaalan API", version="0.1.0")

import os

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    os.getenv("DASHBOARD_BASE_URL", ""),
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(cases_router)
app.include_router(dashboard_router)
app.include_router(directives_router)
app.include_router(audit_router)


# 🔥 ADD THIS BLOCK (CRITICAL)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}

@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}