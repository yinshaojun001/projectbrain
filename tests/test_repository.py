import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.models import ProjectRecord
from projectbrain_runtime.repository import JsonProjectBrainRepository, ProjectBrainRepository


class RepositoryTest(unittest.TestCase):
    def test_json_repository_implements_runtime_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository: ProjectBrainRepository = JsonProjectBrainRepository(tmp)
            repository.ensure()
            project = ProjectRecord(
                project_id="payment_demo",
                name="Payment Demo",
                source_path="/repo/payment",
                codegraph_db_path="/repo/payment/.codegraph/codegraph.db",
            )

            repository.save_project(project)
            repository.save_inventory("payment_demo", {"project_id": "payment_demo", "tables": []})
            repository.save_facts("payment_demo", {"project_id": "payment_demo", "entities": []})
            repository.save_experience_claims("payment_demo", [{"id": "exp"}])
            artifact_path = repository.save_run_artifact("payment_demo", "context-pack-latest.json", {"ok": True})

            self.assertEqual(repository.get_project("payment_demo").name, "Payment Demo")
            self.assertEqual(repository.get_inventory("payment_demo")["project_id"], "payment_demo")
            self.assertEqual(repository.get_facts("payment_demo")["project_id"], "payment_demo")
            self.assertEqual(repository.get_experience_claims("payment_demo")[0]["id"], "exp")
            self.assertTrue(Path(artifact_path).exists())
            self.assertEqual(len(repository.list_projects()), 1)


if __name__ == "__main__":
    unittest.main()
