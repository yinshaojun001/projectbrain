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
            'url "https://github.com/yinshaojun001/projectbrain/archive/7fc38464f6285d76a96d07b6e9010c7564bcc4ca.tar.gz"',
            formula,
        )
        self.assertIn('sha256 "d3f869b874d00901f8ed5bd0433e7b852920cbfb9c0dba684551e499adea33f4"', formula)

    def test_formula_has_local_head_for_checkout_smoke(self):
        formula = FORMULA.read_text()

        self.assertIn('head "https://github.com/yinshaojun001/projectbrain.git", branch: "main"', formula)

    def test_pyproject_exposes_projectbrain_and_codex_brain_scripts(self):
        pyproject = PYPROJECT.read_text()

        self.assertIn('projectbrain = "projectbrain_cli.main:main"', pyproject)
        self.assertIn('codex-brain = "projectbrain_cli.codex_brain:main"', pyproject)
