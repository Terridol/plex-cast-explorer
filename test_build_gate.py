"""Mutation/regression tests: invalid installer edits MUST block local builds."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_gate


class BuildGateRegressionTests(unittest.TestCase):
    def test_valid_baseline_contract(self):
        self.assertEqual(build_gate.check_install_contract(build_gate.ROOT),
                         build_gate.app_version(build_gate.ROOT))

    def assert_mutation_blocked(self, file, original, modified):
        root = build_gate.ROOT
        path = root / file
        text = path.read_text(encoding='utf-8-sig')
        self.assertIn(original, text)
        with patch.object(build_gate, 'read') as read:
            def altered(root_arg, path_arg):
                result = (root_arg / path_arg).read_text(encoding='utf-8-sig')
                return result.replace(original, modified, 1) if path_arg == file else result
            read.side_effect = altered
            with self.assertRaises(build_gate.GateFailure):
                build_gate.check_install_contract(root)

    def test_version_drift_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    '#define AppVersion "0.4.7-beta"',
                                    '#define AppVersion "9.0.0"')

    def test_powershell_version_regex_double_escaping_is_fatal(self):
        # PowerShell preserves backslashes in strings; doubling them silently
        # prevents .NET regex from recognizing app.py's VERSION declaration.
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     r'(?m)^VERSION\s*=', r'(?m)^VERSION\\s*=')

    def test_version_detection_must_precede_compilation(self):
        builder = (build_gate.ROOT / 'build_installer_windows.ps1').read_text(
            encoding='utf-8-sig')
        self.assertLess(builder.index('$appVersionMatch = [regex]::Match'),
                        builder.index("Invoke-Python @('-c'"))

    def test_updater_version_mismatch_is_fatal(self):
        self.assert_mutation_blocked('installer/check_updates.ps1',
                                     "$installed = '0.4.7-beta'",
                                     "$installed = '0.4.6-beta'")

    def test_service_version_mismatch_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     "$ExpectedVersion = '0.4.7-beta'",
                                     "$ExpectedVersion = '0.4.6-beta'")

    def test_dev_build_id_has_strict_format(self):
        build_gate.validate_build_id('dev-20261014-203512123-g23a496e7')
        build_gate.validate_build_id('dev-20261014-203512123-s01234567')
        for bad in ('', '0.4.7-beta', 'dev-20261014-g23a496e7',
                    'dev-20261014-203512123-nohash', '../malicious'):
            with self.subTest(bad=bad), self.assertRaises(build_gate.GateFailure):
                build_gate.validate_build_id(bad)

    def test_missing_dev_build_display_version_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    'AppVersion={#AppVersion}-{#DevBuildId}',
                                    'AppVersion={#AppVersion}')

    def test_missing_installer_build_id_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                    "'/DDevBuildId=' + $buildId",
                                    "'/DDevBuildId=' + ''")

    def test_bypassed_service_readiness_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                    '$health.version -eq $ExpectedVersion',
                                    '$true')

    def test_bypassed_setup_exit_check_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    'if ExitCode <> 0 then',
                                    'if False then')

    def test_public_firewall_scope_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                    '-Profile Private -RemoteAddress $remote',
                                    '-Profile Any -RemoteAddress Any')

    def test_missing_installer_failure_logging_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                    'installer-last-error.txt',
                                    'removed-setup-error-log.txt')

    def test_missing_error_display_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    'LoadStringFromFile(FailurePath, FailureRaw)',
                                    'False')

    def test_unsupported_winsw_refresh_is_fatal(self):
        # Regression: actual WinSW 2.12 rejected 'refresh' and left the
        # installed service stopped after Setup failed with exit code 1.
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                    '& sc.exe config $serviceName start= delayed-auto',
                                    '& $wrapper refresh')

    def test_missing_existing_service_verification_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                    'Get-CimInstance -ClassName Win32_Service',
                                    'Get-Service -Name $serviceName')

    def test_corrupted_git_revision_regex_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                    "$gitHead[-1] -match '^[0-9a-fA-F]{8}$'",
                                    "$gitHead[-1] -match '^[0-9a-fA-F]{8}")

    def test_duplicated_build_body_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                    "# Delete an old artifact first:",
                                    "# Delete an old artifact first: duplicated\\n# Delete an old artifact first:")

    def test_missing_windows_powershell_parse_preflight_is_fatal(self):
        self.assert_mutation_blocked('BUILD-INSTALLER.cmd',
                                    'scripts\\validate_powershell.ps1',
                                    'scripts\\missing_preflight.ps1')

    def test_truncated_updater_filename_regex_is_fatal(self):
        self.assert_mutation_blocked('installer/check_updates.ps1',
                                    "win-x64\\.exe$' } | Select-Object -First 1",
                                    "win-x64\\.exe } | Select-Object -First 1")

    def test_duplicated_updater_download_section_is_fatal(self):
        self.assert_mutation_blocked('installer/check_updates.ps1',
                                    "Start-Process -FilePath $installer -Verb RunAs -Wait",
                                    "Start-Process -FilePath $installer -Verb RunAs -Wait\nStart-Process -FilePath $installer -Verb RunAs -Wait")

    def test_removing_build_stage_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                    "'installer'", "'omitted'")


if __name__ == '__main__':
    unittest.main()