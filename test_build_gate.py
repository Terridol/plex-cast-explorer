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

    def test_removing_build_stage_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                    "'installer'", "'omitted'")


if __name__ == '__main__':
    unittest.main()