# Context store - Shared memory across agents for a project

from typing import Any, Optional, Dict
from datetime import datetime, timezone


class ContextStore:
    """In-memory context store for project shared memory.
    In production, backed by PostgreSQL context_entries table.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, int] = {}

    def set(self, project_id: str, key: str, value: Any):
        """Set a context value for a project."""
        entry_key = f"{project_id}:{key}"
        version = self._versions.get(entry_key, 0) + 1
        self._store[entry_key] = {
            "value": value,
            "version": version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._versions[entry_key] = version

    def get(self, project_id: str, key: str) -> Optional[Any]:
        """Get a context value for a project."""
        entry_key = f"{project_id}:{key}"
        entry = self._store.get(entry_key)
        return entry["value"] if entry else None

    def get_all(self, project_id: str) -> Dict[str, Any]:
        """Get all context entries for a project."""
        return {
            k.split(":", 1)[1]: v["value"]
            for k, v in self._store.items()
            if k.startswith(f"{project_id}:")
        }

    def clear_project(self, project_id: str):
        """Clear all context for a project."""
        keys = [k for k in self._store if k.startswith(f"{project_id}:")]
        for k in keys:
            del self._store[k]
            del self._versions[k]