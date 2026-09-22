"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import init_db
from .routers import files, podcasts, uploads
from .services.seed import seed as seed_datasets


def _startup() -> None:
    init_db()
    try:
        results = seed_datasets(force=False)
        imported = [r for r in results if r["status"] == "imported"]
        if imported:
            print(f"Seeded {len(imported)} podcast(s) from the local datasets.")
    except FileNotFoundError as exc:
        print(f"Seed skipped: {exc}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _startup()
    yield


app = FastAPI(
    title="ListenLab API",
    description="Interactive podcast listening & vocabulary learning platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(podcasts.router)
app.include_router(uploads.router)
app.include_router(files.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces to normal users.
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})


# ---------------------------------------------------------------------------
# Serve the built frontend (single-origin deployment)
# ---------------------------------------------------------------------------
if config.FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(config.FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):  # noqa: ARG001
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found."})
        candidate = config.FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.FRONTEND_DIST / "index.html")
