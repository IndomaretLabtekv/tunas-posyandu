"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import store
from api.routes import router
from api.workflow_routes import router as workflow_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite schema on startup."""
    conn = store.get_conn()
    store.init_db(conn)
    conn.close()
    yield


app = FastAPI(title="Tunas API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(workflow_router, prefix="/api")
