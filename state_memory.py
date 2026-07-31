import os, json, time
from pathlib import Path

MEMORY_FILE = Path("state_memory.json")

class StateMemoryManager:
    def __init__(self, memory_file=MEMORY_FILE):
        self.memory_file = Path(memory_file)
        self.state = self._load_memory()

    def _load_memory(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print("Error loading state memory:", e)
        return {"processed_files": {}, "last_delta_sync": 0}

    def save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print("Error saving state memory:", e)

    def is_file_processed(self, file_key, user_id='default_user'):
        u_key = f"{user_id}::{file_key}"
        return u_key in self.state["processed_files"]

    def mark_processed(self, file_key, category, identity, status="CONFIRMED", confidence=1.0, user_id='default_user'):
        u_key = f"{user_id}::{file_key}"
        self.state["processed_files"][u_key] = {
            "category": category,
            "identity": identity,
            "status": status,
            "confidence": confidence,
            "timestamp": time.time()
        }
        self.save_memory()

    def get_unprocessed_files(self, all_file_items):
        """
        Delta Sync: Filter out any file items that have already been processed
        or manually categorized in state_memory.json.
        """
        unprocessed = []
        for item in all_file_items:
            path_key = str(item.get('path', ''))
            if not self.is_file_processed(path_key):
                unprocessed.append(item)
        return unprocessed

    def update_delta_sync_time(self):
        self.state["last_delta_sync"] = time.time()
        self.save_memory()

# Global Singleton Instance
state_memory = StateMemoryManager()
