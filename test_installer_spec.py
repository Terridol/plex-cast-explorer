"""Static contract tests for the Windows installer and update flow.

Windows service startup and ISCC compilation still require a Windows smoke test.
"""
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parent


class InstallerSpecTests(unittest.TestCase):
    def read(self, path):
        return (BASE / path).read_text(encoding='utf-8')

    def test_stable_product_id_and_upgrades(self):
        spec = self.read('PlexCastExplorer.iss')
        self.assertRegex(spec, r'AppId=\{\{[A-F0-9-]{36}\}')
        self.assertIn('UsePreviousAppDir=yes', spec)
        self.assertIn('UsePreviousTasks=yes', spec)
        self.assertIn('function PrepareToInstall(', spec)
        self.assertIn('configure_service.ps1', spec)
        self.assertNotIn('ExistingDataDir', spec)

    def test_installation_options_and_firewall_scoping(self):
        spec = self.read('PlexCastExplorer.iss')
        setup = self.read('installer/configure_service.ps1')
        self.assertIn('CreateInputQueryPage', spec)
        for option in ('firewall', 'tmdb', 'remoteadmin', 'beta'):
            self.assertIn(f'Name: "{option}"', spec)
        self.assertIn("-Profile Private -RemoteAddress $remote", setup)
        self.assertIn("$remote = @('LocalSubnet') + $addresses", setup)
        self.assertIn('Get-NetFirewallRule -Name $ruleName', setup)
        self.assertNotIn('-Profile Any', setup)
        self.assertNotIn('-Profile Public', setup)
        self.assertRegex(setup, r'WaitForStatus\(\'Running\'')

    def test_service_is_running_before_setup_finish(self):
        spec = self.read('PlexCastExplorer.iss')
        setup = self.read('installer/configure_service.ps1')
        self.assertIn('procedure CurStepChanged(CurStep: TSetupStep)', spec)
        self.assertIn('if CurStep <> ssPostInstall then', spec)
        self.assertIn('ewWaitUntilTerminated', spec)
        self.assertIn('if ExitCode <> 0 then', spec)
        self.assertIn('RaiseException(', spec)
        self.assertIn("-ExpectedVersion ", spec)
        self.assertNotIn('configure_service.ps1', spec.split('[Run]', 1)[1].split('[UninstallRun]', 1)[0])
        self.assertIn("WaitForStatus('Running'", setup)
        self.assertIn('http://127.0.0.1:$Port/api/config', setup)
        self.assertIn('$health.version -eq $ExpectedVersion', setup)
        self.assertIn('if (-not $ready)', setup)

    def test_failed_setup_reports_root_cause(self):
        spec = self.read('PlexCastExplorer.iss')
        service = self.read('installer/configure_service.ps1')
        self.assertIn('FailureRaw: AnsiString', spec)
        self.assertIn('LoadStringFromFile(FailurePath, FailureRaw)', spec)
        self.assertIn('FailureReason := Trim(FailureRaw)', spec)
        self.assertIn('installer-last-error.txt', spec)
        self.assertIn('installer-error-details.log', spec)
        self.assertIn('trap {', service)
        self.assertIn('exit 1', service)
        self.assertIn('Set-Content -LiteralPath $installerErrorFile', service)

    def test_upgrade_does_not_delete_local_data(self):
        setup = self.read('installer/configure_service.ps1')
        uninstall = self.read('installer/uninstall_cleanup.ps1')
        self.assertIn("$dataDir ('backups", setup)
        self.assertIn("'cast_explorer.db-wal'", setup)
        self.assertIn("& $wrapper refresh", setup)
        self.assertIn("$serviceName = 'PlexCastExplorer'", setup)
        self.assertNotIn('Remove-Item -Recurse -Force $dataDir', setup + uninstall)
        self.assertIn('Stop-Service', uninstall)
        self.assertIn('Remove-NetFirewallRule', uninstall)

    def test_updates_are_consented_and_hash_verified(self):
        checker = self.read('installer/check_updates.ps1')
        self.assertIn('api.github.com/repos/', checker)
        self.assertIn('DownloadAndInstall', checker)
        self.assertIn('Get-FileHash', checker)
        self.assertIn("^sha256:", checker)
        self.assertIn("$answer -cne 'YES'", checker)
        self.assertIn('Start-Process -FilePath $installer -Verb RunAs', checker)

    def test_install_kit_has_build_pipeline(self):
        self.assertIn('BUILD-EXE.cmd', self.read('build_installer_windows.ps1'))
        self.assertIn('WinSW-x64.exe', self.read('build_installer_windows.ps1'))
        self.assertIn('ISCC.exe', self.read('build_installer_windows.ps1'))
        self.assertIn('PlexCastExplorer-Setup-0.4.7-beta-win-x64.exe', self.read('build_installer_windows.ps1'))
        self.assertEqual(re.search(r"^VERSION = '([^']+)'", self.read('app.py'), re.M).group(1), '0.4.7-beta')


if __name__ == '__main__':
    unittest.main()
