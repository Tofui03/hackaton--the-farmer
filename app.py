from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.middleware import TimingMiddleware
from src.api.routes import router

app = FastAPI(
    title="Shipping Document Verification & Audit API",
    description="Shipping document verification, deterministic comparison, evidence tracing, and human review API.",
    version="1.0.0",
)

# Local Vite development and separately hosted static deployments may use a
# different origin. Production environments can narrow this policy externally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)

app.include_router(router)

# T14: a Vite production build writes to docs/. Only mount the SPA when the
# build assets exist, so the preserved legacy prototype is never served as the
# production console by accident.
_docs_dir = Path(__file__).resolve().parent / "docs"
_assets_dir = _docs_dir / "assets"
if _assets_dir.is_dir() and (_docs_dir / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend-assets")

    @app.get("/cases", include_in_schema=False)
    @app.get("/cases/{spa_path:path}", include_in_schema=False)
    def serve_frontend(spa_path: str = ""):
        return FileResponse(_docs_dir / "index.html")


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
