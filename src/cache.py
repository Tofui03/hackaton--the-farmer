import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PipelineCache:
    """Persistent JSON cache for pipeline checkpoints."""

    def __init__(self, cache_file: str = ".cache_pipeline.json"):
        self.cache_file = Path(cache_file)
        self.data: Dict[str, Any] = {
            "classifications": {},
            "comparisons": {},
            "extractions": {},
        }
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                content = self.cache_file.read_text(encoding="utf-8")
                loaded = json.loads(content)
                self.data["classifications"] = loaded.get("classifications", {})
                self.data["comparisons"] = loaded.get("comparisons", {})
                self.data["extractions"] = loaded.get("extractions", {})
                logger.info("Loaded pipeline cache from %s", self.cache_file)
            except Exception as e:
                logger.warning("Failed to load cache from %s: %s", self.cache_file, e)

    def save(self):
        try:
            self.cache_file.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save cache to %s: %s", self.cache_file, e)

    def get_classification(self, email_id: str) -> Optional[str]:
        return self.data["classifications"].get(email_id)

    def set_classification(self, email_id: str, category: str):
        self.data["classifications"][email_id] = category

    def get_comparison(self, email_id: str) -> Optional[Dict[str, Any]]:
        return self.data["comparisons"].get(email_id)

    def set_comparison(self, email_id: str, result: Dict[str, Any]):
        self.data["comparisons"][email_id] = result

    def get_extraction(self, att_path: str) -> Optional[Dict[str, Any]]:
        return self.data["extractions"].get(att_path)

    def set_extraction(self, att_path: str, info: Dict[str, Any]):
        self.data["extractions"][att_path] = info

    def clear(self):
        self.data = {"classifications": {}, "comparisons": {}, "extractions": {}}
        if self.cache_file.exists():
            self.cache_file.unlink()
