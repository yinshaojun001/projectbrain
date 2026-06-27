import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.knowledge_store import SQLiteKnowledgeStore  # noqa: E402


class SQLiteKnowledgeStoreTest(unittest.TestCase):
    def test_ensure_creates_v1_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "knowledge.db"
            store = SQLiteKnowledgeStore(db_path)

            store.ensure()

            connection = sqlite3.connect(db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
            finally:
                connection.close()

            self.assertIn("knowledge_units", table_names)
            self.assertIn("claims", table_names)
            self.assertIn("evidence_items", table_names)
            self.assertIn("entity_links", table_names)
            self.assertIn("review_events", table_names)
            self.assertIn("quality_flags", table_names)


if __name__ == "__main__":
    unittest.main()
