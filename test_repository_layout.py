"""Repository hygiene tests for the supported Windows service distribution."""
from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parent

OBSOLETE = (
    "manage.py",
    "BUILD-EXE.cmd",
    "build_windows_exe.ps1",
    "installer/stop_for_upgrade.ps1",
    "start_windows.bat",
    "start_linux_mac.sh",
    "set_password_windows.bat",
    "START-HERE.txt",
    "docs/INSTALLATION.md",
    "docs/WINDOWS_SERVICE.md",
    "docs/PUBLICATION_STATUS.md",
    "docs/BETA_RELEASE_CHECKLIST.md",
    "docs/BRANCHING.md",
    "docs/RELEASE.md",
    "docs/MAINTAINERS.md",
    "legal/CONTRIBUTOR_LICENSE_AGREEMENT_PROPOSAL.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/CODEOWNERS",
)
REQUIRED = (
    "app.py",
    "docs/RELEASE_CHECKLIST.md",
    "docs/RELEASE_NOTES_1_0.md",
    "PlexCastExplorer.iss",
    "BUILD-INSTALLER.cmd",
    "build_installer_windows.ps1",
    "build_gate.py",
    "scripts/validate_powershell.ps1",
    "installer/configure_service.ps1",
    "installer/configure_password.ps1",
    "installer/check_updates.ps1",
    "installer/uninstall_cleanup.ps1",
    "LICENSE",
    "legal/WinSW-LICENSE.txt",
)


class RepositoryLayoutTests(unittest.TestCase):
    def test_single_supported_windows_workflow(self):
        for path in OBSOLETE:
            with self.subTest(obsolete=path):
                self.assertFalse((ROOT / path).exists(), f"Retired file returned: {path}")
        for path in REQUIRED:
            with self.subTest(required=path):
                self.assertTrue((ROOT / path).is_file(), f"Required Windows file missing: {path}")

    def test_no_redundant_windows_launchers_or_unvalidated_scripts(self):
        # The Windows service/installer distribution intentionally has one
        # CMD entry point and exactly six purpose-specific PowerShell files.
        batch = {p.relative_to(ROOT).as_posix()
                 for p in list(ROOT.glob('*.cmd')) + list(ROOT.glob('*.bat'))}
        self.assertEqual(batch, {'BUILD-INSTALLER.cmd'})
        powershell = {p.relative_to(ROOT).as_posix()
                      for folder in (ROOT, ROOT / 'installer', ROOT / 'scripts')
                      for p in folder.glob('*.ps1')}
        self.assertEqual(powershell, {
            'build_installer_windows.ps1',
            'installer/check_updates.ps1',
            'installer/configure_password.ps1',
            'installer/configure_service.ps1',
            'installer/uninstall_cleanup.ps1',
            'scripts/validate_powershell.ps1',
        })
        parser = (ROOT / 'scripts/validate_powershell.ps1').read_text(encoding='utf-8')
        self.assertIn("Get-ChildItem -LiteralPath $directory -Filter '*.ps1' -File", parser)
        self.assertIn("Join-Path $root 'installer'", parser)
        self.assertIn("Join-Path $root 'scripts'", parser)
        self.assertIn('[System.Management.Automation.Language.Parser]::ParseFile(', parser)

    def test_python_files_parse_without_duplicate_module_functions(self):
        for path in ROOT.rglob("*.py"):
            if any(part in {"build", "dist", "output", ".venv", "venv", "__pycache__", ".git", "installer-assets"} for part in path.parts):
                continue
            with self.subTest(source=str(path.relative_to(ROOT))):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                names = [
                    (node.name, type(node).__name__)
                    for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                ]
                self.assertEqual(len(names), len(set(names)), "Duplicate Python module definition")
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        methods = [
                            child.name for child in node.body
                            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        self.assertEqual(len(methods), len(set(methods)),
                                         f"Duplicate method in {node.name}")
                main_guards = [
                    node for node in tree.body
                    if isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__"
                ]
                self.assertLessEqual(len(main_guards), 1,
                                     "Duplicate Python __main__ block")

    def test_local_markdown_links_resolve(self):
        # Internal doc links cannot refer to files removed by cleanup.
        pattern = re.compile(r"\]\(([^)]+)\)")
        for path in (list(ROOT.glob("*.md")) +
                     list((ROOT / "docs").rglob("*.md")) +
                     list((ROOT / "legal").rglob("*.md"))):
            text = path.read_text(encoding="utf-8-sig")
            for raw in pattern.findall(text):
                target = raw.split("#", 1)[0].strip().strip("<>")
                if (not target or "://" in target or
                        target.startswith(("mailto:", "/", "#"))):
                    continue
                with self.subTest(file=path.name, link=target):
                    self.assertTrue((path.parent / target).exists(),
                                    f"Broken link in {path.relative_to(ROOT)}: {raw}")

    def test_private_runtime_artifacts_are_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for rule in ("config.json", "auth.json", "admin_auth.json", "*.db",
                     "portraits/", "output/", "dist/", "installer-assets/"):
            self.assertIn(rule, gitignore)


if __name__ == "__main__":
    unittest.main()
