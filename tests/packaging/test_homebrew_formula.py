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
        self.assertRegex(
            formula,
            re.compile(
                r'shell_output\("#\{bin\}/codex-brain --project #\{testpath\}/repo --no-ui --no-extract --codex-command true"\)'
            ),
        )

    def test_formula_stable_archive_points_to_codex_brain_commit(self):
        formula = FORMULA.read_text()

        self.assertIn(
            'url "https://github.com/yinshaojun001/projectbrain/archive/f1817cf.tar.gz"',
            formula,
        )
        self.assertIn('sha256 "001bccdbe747daaf768e83754c9e8fcf5a73f58c56c28abeabd13149b20a8f68"', formula)

    def test_formula_has_local_head_for_checkout_smoke(self):
        formula = FORMULA.read_text()

        self.assertIn('head "https://github.com/yinshaojun001/projectbrain.git", branch: "main"', formula)

    def test_pyproject_exposes_projectbrain_and_codex_brain_scripts(self):
        pyproject = PYPROJECT.read_text()

        self.assertIn('projectbrain = "projectbrain_cli.main:main"', pyproject)
        self.assertIn('codex-brain = "projectbrain_cli.codex_brain:main"', pyproject)
