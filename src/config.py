import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or current working directory
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Optional Google Cloud Document AI
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
DOCAI_PROJECT_ID = os.getenv("DOCAI_PROJECT_ID", "")
DOCAI_LOCATION = os.getenv("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID = os.getenv("DOCAI_PROCESSOR_ID", "")


def is_gemini_available() -> bool:
    """Return True if Gemini API key is configured."""
    return bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())


def is_docai_available() -> bool:
    """Return True if GCP Document AI credentials and processor are configured."""
    return bool(
        (GOOGLE_APPLICATION_CREDENTIALS or os.getenv("GOOGLE_CLOUD_PROJECT"))
        and DOCAI_PROJECT_ID
        and DOCAI_PROCESSOR_ID
    )
