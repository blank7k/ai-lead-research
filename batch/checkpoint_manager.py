import os
import json
import threading
from typing import List
from loguru import logger


class CheckpointManager:
    """Manages persistence of processed brands in data/checkpoint.json to support Ctrl+C resuming."""

    def __init__(self, filepath: str = "data/checkpoint.json") -> None:
        self.filepath = filepath
        self._lock = threading.Lock()
        
    def load_completed(self) -> List[str]:
        """Load the list of completed brand names from the checkpoint file."""
        with self._lock:
            if not os.path.exists(self.filepath):
                return []
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("completed", [])
            except Exception as e:
                logger.error(f"Failed to load checkpoint file '{self.filepath}': {e}")
                return []

    def save_completed(self, completed: List[str]) -> None:
        """Saves the list of completed brands to the checkpoint file atomatically."""
        with self._lock:
            dir_name = os.path.dirname(self.filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            try:
                # Write to temp file and rename to avoid corruption during interruption (Ctrl+C)
                temp_path = self.filepath + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump({"completed": completed}, f, indent=4)
                
                # Windows doesn't allow atomic replace of existing files by rename: delete if exists
                if os.path.exists(self.filepath):
                    os.remove(self.filepath)
                os.rename(temp_path, self.filepath)
                logger.debug(f"Saved {len(completed)} completed brands to checkpoint: {self.filepath}")
            except Exception as e:
                logger.error(f"Failed to save checkpoint to '{self.filepath}': {e}")

    def add_completed(self, brand_name: str) -> None:
        """Add a single completed brand name and commit to disk immediately."""
        completed = self.load_completed()
        if brand_name not in completed:
            completed.append(brand_name)
            self.save_completed(completed)

    def clear(self) -> None:
        """Clears/removes the checkpoint file."""
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                    logger.info(f"Cleared checkpoint: '{self.filepath}'")
                except Exception as e:
                    logger.error(f"Failed to clear checkpoint: {e}")
