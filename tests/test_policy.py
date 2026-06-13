import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.policy import (  # noqa: E402
    ProjectBrainPolicy,
    apply_output_policy,
    inspect_policy_for_project,
    load_policy_for_project,
)


class ProjectBrainPolicyTest(unittest.TestCase):
    def test_apply_output_policy_filters_denied_paths_caps_lists_and_strips_snippets(self):
        artifact = {
            "sections": [
                {
                    "type": "important_entities",
                    "items": [
                        {
                            "file": "public/src/App.java",
                            "body": "class App {}",
                            "sources": [{"locator": {"file": "public/src/App.java"}}],
                        },
                        {
                            "file": "private/src/Secret.java",
                            "snippet": "secret",
                            "sources": [{"locator": {"file": "private/src/Secret.java"}}],
                        },
                    ],
                }
            ],
            "recommended_files": [
                {"file": "public/src/App.java", "reason": "public"},
                {"file": "private/src/Secret.java", "reason": "private"},
            ],
            "recommended_tests": [
                {"file": "public/test/AppTest.java"},
                {"file": "public/test/OtherTest.java"},
            ],
        }

        filtered = apply_output_policy(
            artifact,
            ProjectBrainPolicy(
                deny_paths=["private/**"],
                max_items_per_section=1,
                max_recommended_files=1,
                max_recommended_tests=1,
            ),
        )

        self.assertEqual(
            filtered["sections"][0]["items"],
            [{"file": "public/src/App.java", "sources": [{"locator": {"file": "public/src/App.java"}}]}],
        )
        self.assertEqual(filtered["recommended_files"], [{"file": "public/src/App.java", "reason": "public"}])
        self.assertEqual(filtered["recommended_tests"], [{"file": "public/test/AppTest.java"}])

    def test_load_policy_from_project_json_and_simple_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / ".projectbrain-policy.json"
            json_path.write_text(
                '{"deny_paths":["private/**"],"output_limits":{"max_recommended_files":2}}',
                encoding="utf-8",
            )

            policy = load_policy_for_project(root)

            self.assertEqual(policy.deny_paths, ["private/**"])
            self.assertEqual(policy.max_recommended_files, 2)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / ".projectbrain-policy.yml"
            yaml_path.write_text(
                "\n".join(
                    [
                        "deny_paths:",
                        "  - private/**",
                        "max_items_per_section: 3",
                        "include_source_snippets: false",
                    ]
                ),
                encoding="utf-8",
            )

            policy = load_policy_for_project(root)

            self.assertEqual(policy.deny_paths, ["private/**"])
            self.assertEqual(policy.max_items_per_section, 3)
            self.assertFalse(policy.include_source_snippets)

    def test_inspect_policy_reports_source_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy_path = root / ".projectbrain-policy.json"
            policy_path.write_text(
                '{"deny_paths":["private/**"],"max_recommended_tests":0,"include_source_snippets":false}',
                encoding="utf-8",
            )

            output = inspect_policy_for_project(root)

            self.assertTrue(output["policy_found"])
            self.assertEqual(output["source_path"], str(policy_path))
            self.assertEqual(output["summary"]["deny_path_count"], 1)
            self.assertTrue(output["summary"]["has_output_caps"])
            self.assertFalse(output["summary"]["source_snippets_enabled"])


if __name__ == "__main__":
    unittest.main()
