import json
import os
from datetime import datetime
from src.utils import logger

class Storage:
    def __init__(self, file_path):
        self.file_path = file_path
        self._ensure_dir()

    def _ensure_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def load(self):
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode state file: {self.file_path}, returning empty state.")
            return {}
        except Exception as e:
            logger.error(f"Error loading state file: {e}")
            return {}

    def save(self, data):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")

    def get_last_version(self):
        state = self.load()
        return state.get("last_version")

    def update_last_version(self, version):
        state = self.load()
        state["last_version"] = version
        state["last_checked_at"] = datetime.now().isoformat()
        self.save(state)

    def mark_notified(self, version):
        state = self.load()
        now = datetime.now().isoformat()
        state["last_version"] = version
        state["last_notified_version"] = version
        state["last_checked_at"] = now
        state["last_notified_at"] = now
        self.save(state)
