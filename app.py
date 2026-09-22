from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

app = FastAPI(
    title="Shipping Document Verification & Audit API",
    description="Production-grade AI Shipping Document Verification Engine featuring Zero False Alarms, Strict Golden SI Anchoring, and HITL Fallback.",
    version="1.0.0",
)

# Enable CORS for GitHub Pages frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
