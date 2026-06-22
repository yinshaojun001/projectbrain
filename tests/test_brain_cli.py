import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))

from projectbrain_cli.main import main  # noqa: E402


class BrainCliTest(unittest.TestCase):
    def test_brain_remember_list_search_and_confirm_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            store_root = str(Path(tmp) / "store")

            remember = _run_cli([
                "--store-root", store_root,
                "brain", "remember", str(project_path),
                "--id", "payment",
                "--type", "constraint",
                "--statement", "Refund fee must not affect settlement principal.",
                "--tag", "refund",
                "--applies-to", "RefundService",
                "--review-state", "human_confirmed",
            ])
            self.assertEqual(remember["knowledge_unit"]["review_state"], "human_confirmed")

            listed = _run_cli(["--store-root", store_root, "brain", "list", str(project_path)])
            self.assertEqual(listed["knowledge_unit_count"], 1)

            search = _run_cli(["--store-root", store_root, "brain", "search", str(project_path), "refund"])
            self.assertEqual(search["matches"][0]["review_state"], "human_confirmed")

            proposed = _run_cli([
                "--store-root", store_root,
                "brain", "propose", str(project_path),
                "--id", "payment",
                "--type", "gotcha",
                "--statement", "account_record is append-only.",
                "--tag", "account",
            ])
            candidate_id = proposed["candidates"][0]["candidate_id"]

            confirmed = _run_cli([
                "--store-root", store_root,
                "brain", "confirm-candidate", str(project_path), candidate_id,
            ])
            self.assertEqual(confirmed["knowledge_unit"]["type"], "gotcha")


def _run_cli(args):
    stdout = StringIO()
    with redirect_stdout(stdout):
        return_code = main(args)
    if return_code != 0:
        raise AssertionError(f"CLI returned {return_code}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
