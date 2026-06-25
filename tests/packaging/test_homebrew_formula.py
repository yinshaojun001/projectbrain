import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMULA = ROOT / "Formula" / "projectbrain.rb"
PYPROJECT = ROOT / "pyproject.toml"


class HomebrewFormulaPackagingTest(unittest.TestCase):
    def test_formula_smoke_tests_all_installed_entrypoints(self):
        formula = FORMULA.read_text()

        self.assertIn('shell_output("#{bin}/projectbrain --help")', formula)
        self.assertIn('shell_output("#{bin}/codex-brain --help")', formula)
        self.assertIn('shell_output("#{bin}/projectbrain brain --help")', formula)
        self.assertIn('import fastapi, uvicorn, jinja2, projectbrain_api', formula)
        self.assertRegex(
            formula,
            re.compile(
                r'shell_output\("#\{bin\}/codex-brain --project #\{testpath\}/repo --no-ui --no-extract --codex-command true"\)'
            ),
        )
        self.assertIn('refute_path_exists testpath/"repo"/".projectbrain"/"brain"/"conversations.jsonl"', formula)

    def test_formula_stable_archive_points_to_codex_brain_commit(self):
        formula = FORMULA.read_text()

        self.assertIn(
            'url "https://github.com/yinshaojun001/projectbrain/archive/4134985f241af51954e4ccc09e327b6fe239464f.tar.gz"',
            formula,
        )
        self.assertIn('sha256 "ca385a989e809f37f1c05701f9592fd2a9ebd9e1d6ad70f1f24f9e5dfd7cc5c3"', formula)

    def test_formula_has_local_head_for_checkout_smoke(self):
        formula = FORMULA.read_text()

        self.assertIn('head "https://github.com/yinshaojun001/projectbrain.git", branch: "main"', formula)

    def test_pyproject_exposes_projectbrain_and_codex_brain_scripts(self):
        pyproject = PYPROJECT.read_text()

        self.assertIn('projectbrain = "projectbrain_cli.main:main"', pyproject)
        self.assertIn('codex-brain = "projectbrain_cli.codex_brain:main"', pyproject)

    def test_pyproject_packages_ui_templates_and_static_assets(self):
        pyproject = PYPROJECT.read_text()

        self.assertIn("[tool.setuptools.package-data]", pyproject)
        self.assertIn('"projectbrain_api.ui" = ["templates/**/*.html", "static/**/*.css"', pyproject)
