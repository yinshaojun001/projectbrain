import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.policy import ProjectBrainPolicy, apply_output_policy, load_policy_for_project  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
