import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))

from projectbrain_runtime.models import ProjectRecord
from projectbrain_runtime.store import ProjectBrainStore


class RuntimeStoreTest(unittest.TestCase):
    def test_project_facts_and_run_artifact_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectBrainStore(tmp)
            store.ensure()
            project = ProjectRecord(
                project_id="payment_demo",
                name="Payment Demo",
                source_path="/repo/payment",
                codegraph_db_path="/repo/payment/.codegraph/codegraph.db",
            )

            store.write_project(project)
            store.write_facts("payment_demo", {"project_id": "payment_demo", "entities": []})
            artifact = store.write_run_artifact("payment_demo", "context-pack-latest.json", {"ok": True})

            self.assertEqual(store.read_project("payment_demo").name, "Payment Demo")
            self.assertEqual(store.read_facts("payment_demo")["project_id"], "payment_demo")
            self.assertTrue(artifact.exists())
            self.assertEqual(len(store.list_projects()), 1)


if __name__ == "__main__":
    unittest.main()
