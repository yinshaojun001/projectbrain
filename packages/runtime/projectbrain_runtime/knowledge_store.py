"""SQLite knowledge store bootstrap for ProjectBrain V1."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteKnowledgeStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def ensure(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_units (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  knowledge_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  statement TEXT NOT NULL,
                  summary TEXT,
                  status TEXT NOT NULL,
                  review_state TEXT NOT NULL,
                  confidence REAL NOT NULL DEFAULT 0.5,
                  risk_level TEXT,
                  source_type TEXT NOT NULL,
                  last_verified_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claims (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  knowledge_unit_id TEXT,
                  claim_type TEXT NOT NULL,
                  statement TEXT NOT NULL,
                  scope_type TEXT,
                  scope_key TEXT,
                  review_state TEXT NOT NULL,
                  confidence REAL NOT NULL DEFAULT 0.5,
                  risk_level TEXT,
                  source_type TEXT NOT NULL,
                  last_verified_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence_items (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  evidence_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  uri TEXT,
                  content_hash TEXT,
                  version_ref TEXT,
                  source_root TEXT,
                  retrieval_status TEXT NOT NULL,
                  last_checked_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS entity_links (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  entity_type TEXT NOT NULL,
                  entity_key TEXT NOT NULL,
                  link_type TEXT NOT NULL,
                  strength REAL NOT NULL DEFAULT 1.0,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_events (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  actor TEXT,
                  before_state_json TEXT,
                  after_state_json TEXT,
                  note TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quality_flags (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  flag_type TEXT NOT NULL,
                  severity TEXT NOT NULL,
                  status TEXT NOT NULL,
                  reason TEXT,
                  detected_by TEXT,
                  created_at TEXT NOT NULL,
                  resolved_at TEXT
                );
                """
            )
            connection.commit()
        finally:
            connection.close()
