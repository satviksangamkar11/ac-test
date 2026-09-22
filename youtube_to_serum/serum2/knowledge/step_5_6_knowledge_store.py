"""
STEP 5.6 — CANONICAL KNOWLEDGE STORE IMPLEMENTATION

Persistent storage layer for normalized KnowledgeItems.
Supports:
  - insert/get/exists/query/count/list operations
  - provenance tracing (knowledge_item_id → proposition_id → source_id → segments)
  - round-trip persistence (store/reload across process restart)
  - atomic writes (safe against corruption)
  - structural queries only (no semantic retrieval in 5.6)
  - no backend-specific coupling
  - UNKNOWN item preservation
  - duplicate handling (idempotent identical, reject conflicting)
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from tempfile import NamedTemporaryFile
import os

from knowledge_item import KnowledgeItem, KnowledgeType, EpistemicStatus


class KnowledgeConflictError(Exception):
    """Raised when attempting to insert conflicting knowledge_item_id with different content."""
    pass


class KnowledgeStore:
    """
    File-backed canonical knowledge store.

    Storage format: JSON array of KnowledgeItem dictionaries.
    Safe write strategy: temp file -> flush -> atomic replace.
    """

    def __init__(self, store_path: str, create_if_missing: bool = True):
        """
        Initialize store.

        Args:
            store_path: Path to the canonical store JSON file
            create_if_missing: If True, create empty store if file doesn't exist
        """
        self.store_path = Path(store_path)
        self.version = "1.0"
        self.schema_version = "5.2"

        if self.store_path.exists():
            # Check if file is empty or corrupt
            try:
                self._load()
            except (json.JSONDecodeError, ValueError):
                if create_if_missing:
                    self._init_empty()
                else:
                    raise
        elif create_if_missing:
            self._init_empty()
        else:
            raise FileNotFoundError(f"Store not found: {self.store_path}")

    def _init_empty(self):
        """Initialize empty store."""
        self.store_data = {
            "version": self.version,
            "schema_version": self.schema_version,
            "created_timestamp": datetime.now().isoformat() + "Z",
            "last_modified": datetime.now().isoformat() + "Z",
            "total_items": 0,
            "items": {}
        }
        self._persist()

    def _load(self):
        """Load store from disk."""
        with open(self.store_path, 'r', encoding='utf-8') as f:
            self.store_data = json.load(f)

    def _persist(self):
        """Persist store to disk using atomic write strategy."""
        self.store_data["last_modified"] = datetime.now().isoformat() + "Z"
        self.store_data["total_items"] = len(self.store_data.get("items", {}))

        # Atomic write: temp file -> flush -> replace
        temp_dir = self.store_path.parent
        with NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.tmp',
            dir=temp_dir,
            delete=False
        ) as tmp:
            json.dump(self.store_data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = tmp.name

        # Atomic replace
        try:
            if self.store_path.exists():
                backup_path = self.store_path.with_suffix('.backup')
                self.store_path.replace(backup_path)
            Path(temp_path).replace(self.store_path)
        except Exception as e:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            raise RuntimeError(f"Failed to persist store: {e}")

    def insert(self, item: KnowledgeItem) -> bool:
        """
        Insert a KnowledgeItem into the store.

        Args:
            item: KnowledgeItem to insert

        Returns:
            True if inserted, False if idempotent (same ID + same content)

        Raises:
            KnowledgeConflictError if same ID with different content
        """
        item_id = item.knowledge_item_id
        item_dict = item.to_dict()

        if item_id in self.store_data["items"]:
            existing = self.store_data["items"][item_id]

            # Compare content
            if existing == item_dict:
                # Idempotent: same ID + same content
                return False
            else:
                # Conflict: same ID + different content
                raise KnowledgeConflictError(
                    f"Conflicting content for knowledge_item_id {item_id}. "
                    f"Use get() to inspect existing item."
                )

        # New item: insert and persist
        self.store_data["items"][item_id] = item_dict
        self._persist()
        return True

    def get(self, knowledge_item_id: str) -> Optional[KnowledgeItem]:
        """
        Retrieve a KnowledgeItem by ID.

        Args:
            knowledge_item_id: The ID to retrieve

        Returns:
            KnowledgeItem if found, None otherwise
        """
        if knowledge_item_id not in self.store_data["items"]:
            return None

        item_dict = self.store_data["items"][knowledge_item_id]
        return KnowledgeItem.from_dict(item_dict)

    def exists(self, knowledge_item_id: str) -> bool:
        """Check if a knowledge_item_id exists in the store."""
        return knowledge_item_id in self.store_data["items"]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count items matching optional filters.

        Args:
            filters: Dict of field → value to match
                    Supported: knowledge_type, epistemic_status, source_id, etc.

        Returns:
            Count of matching items
        """
        if not filters:
            return len(self.store_data["items"])

        count = 0
        for item_dict in self.store_data["items"].values():
            if self._matches_filters(item_dict, filters):
                count += 1
        return count

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[KnowledgeItem]:
        """
        List items matching optional filters.

        Args:
            filters: Dict of field → value to match
            limit: Max items to return

        Returns:
            List of matching KnowledgeItems
        """
        results = []
        for item_dict in self.store_data["items"].values():
            if not filters or self._matches_filters(item_dict, filters):
                results.append(KnowledgeItem.from_dict(item_dict))
                if limit and len(results) >= limit:
                    break
        return results

    def query(self, filters: Dict[str, Any]) -> List[KnowledgeItem]:
        """
        Query items by structural filters.

        Supported filters:
          - knowledge_type: str (e.g., "CONCEPT")
          - epistemic_status: str (e.g., "SOURCE_REPORTED")
          - source_id: str
          - has_ambiguity: bool (True = has ambiguity field)
          - has_unknown_status: bool (True = epistemic_status == UNKNOWN)

        Returns:
            List of matching KnowledgeItems
        """
        results = []
        for item_dict in self.store_data["items"].values():
            if self._matches_query(item_dict, filters):
                results.append(KnowledgeItem.from_dict(item_dict))
        return results

    def get_by_source(self, source_id: str) -> List[KnowledgeItem]:
        """
        Retrieve all KnowledgeItems from a specific source.

        Args:
            source_id: The source ID (e.g., "yt_74ab96e1f377")

        Returns:
            List of KnowledgeItems from that source
        """
        return self.query({"source_id": source_id})

    def get_unknown_items(self) -> List[KnowledgeItem]:
        """Retrieve all UNKNOWN epistemic_status items."""
        return self.query({"has_unknown_status": True})

    def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Validate all items in the store.

        Returns:
            (all_valid, list_of_errors)
        """
        errors = []
        for item_id, item_dict in self.store_data["items"].items():
            try:
                item = KnowledgeItem.from_dict(item_dict)
                valid, item_errors = item.validate()
                if not valid:
                    errors.extend([f"[{item_id}] {e}" for e in item_errors])
            except Exception as e:
                errors.append(f"[{item_id}] Failed to deserialize: {e}")

        return (len(errors) == 0, errors)

    def _matches_filters(self, item_dict: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if item_dict matches all filters."""
        for key, value in filters.items():
            if key == "knowledge_type":
                if item_dict.get("knowledge_type") != value:
                    return False
            elif key == "epistemic_status":
                if item_dict.get("epistemic_status") != value:
                    return False
            elif key == "source_id":
                src_ref = item_dict.get("source_reference", {})
                if src_ref.get("source_id") != value:
                    return False
            else:
                # Direct field match
                if item_dict.get(key) != value:
                    return False
        return True

    def _matches_query(self, item_dict: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if item_dict matches query filters."""
        for key, value in filters.items():
            if key == "knowledge_type":
                if item_dict.get("knowledge_type") != value:
                    return False
            elif key == "epistemic_status":
                if item_dict.get("epistemic_status") != value:
                    return False
            elif key == "source_id":
                src_ref = item_dict.get("source_reference", {})
                if src_ref.get("source_id") != value:
                    return False
            elif key == "has_ambiguity":
                has_ambiguity = item_dict.get("ambiguity") is not None
                if has_ambiguity != value:
                    return False
            elif key == "has_unknown_status":
                is_unknown = item_dict.get("epistemic_status") == "UNKNOWN"
                if is_unknown != value:
                    return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        items = self.store_data.get("items", {})

        # Count by type
        by_type = {}
        by_status = {}
        unknown_count = 0

        for item_dict in items.values():
            ktype = item_dict.get("knowledge_type")
            by_type[ktype] = by_type.get(ktype, 0) + 1

            estatus = item_dict.get("epistemic_status")
            by_status[estatus] = by_status.get(estatus, 0) + 1

            if estatus == "UNKNOWN":
                unknown_count += 1

        return {
            "total_items": len(items),
            "by_type": by_type,
            "by_status": by_status,
            "unknown_items": unknown_count,
            "version": self.version,
            "schema_version": self.schema_version,
            "created": self.store_data.get("created_timestamp"),
            "last_modified": self.store_data.get("last_modified"),
        }
