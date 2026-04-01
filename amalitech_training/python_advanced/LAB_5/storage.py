from __future__ import annotations
"""Asynchronous JSON persistence utilities for LAB_5 scrape outputs."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import aiofiles
except ModuleNotFoundError:
    aiofiles = None  # type: ignore

logger = logging.getLogger(__name__)

# Default destination for generated JSON result files.
OUTPUT_DIR = Path("output")


def ensure_output_dir(path: Path = None) -> Path:
    """Create directory if it does not exist. Returns the path."""
    if path is None:
        path = OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_filename(prefix: str = "results") -> Path:
    """Build a timestamped .json filename inside OUTPUT_DIR."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ensure_output_dir(OUTPUT_DIR) / f"{prefix}_{ts}.json"


async def save_results(results: List[Dict[str, Any]], path: Path = None) -> Path:
    """Write results list to JSON asynchronously. Returns the file path."""
    if path is None:
        path = build_filename()
    payload = json.dumps(results, indent=2, default=str)
    if aiofiles is not None:
        async with aiofiles.open(path, "w", encoding="utf-8") as fh:
            await fh.write(payload)
    else:
        # Fallback for tests when aiofiles is unavailable.
        path.write_text(payload, encoding="utf-8")
    logger.info("saved %d results to %s", len(results), path)
    return path


async def load_results(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON file written by save_results()."""
    if aiofiles is not None:
        async with aiofiles.open(path, encoding="utf-8") as fh:
            content = await fh.read()
    else:
        # Fallback for tests when aiofiles is unavailable.
        content = path.read_text(encoding="utf-8")
    return json.loads(content)
