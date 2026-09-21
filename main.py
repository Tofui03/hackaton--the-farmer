import os
import uvicorn
from app import app

# Expose app for ASGI servers running 'uvicorn main:app'
__all__ = ["app"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
