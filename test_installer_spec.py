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

    def test_python_runtime_license_and_notice_are_packaged(self):
        spec = self.read('PlexCastExplorer.iss')
        builder = self.read('build_installer_windows.ps1')
        self.assertIn('Source: "NOTICE"; DestDir: "{app}"', spec)
        self.assertIn("sys.base_prefix", builder)
        self.assertIn("Python-LICENSE.txt", builder)
        self.assertIn("Copy-Item -LiteralPath $runtimeLicense[0]", builder)

    def test_winsw_mit_notice_is_packaged(self):
        spec = self.read('PlexCastExplorer.iss')
        license_text = self.read('legal/WinSW-LICENSE.txt')
        self.assertIn('Source: "legal\\WinSW-LICENSE.txt"; DestDir: "{app}\\licenses"', spec)
        self.assertIn('MIT License', license_text)
        self.assertIn('Kohsuke Kawaguchi', license_text)

    def test_stable_product_id_and_upgrades(self):
        spec = self.read('PlexCastExplorer.iss')
        self.assertRegex(spec, r'AppId=\{\{[A-F0-9-]{36}\}')
        self.assertIn('UsePreviousAppDir=yes', spec)
        self.assertIn('UsePreviousTasks=yes', spec)
        self.assertIn('function PrepareToInstall(', spec)
        self.assertIn('configure_service.ps1', spec)
        self.assertNotIn('ExistingDataDir', spec)

    def test_dev_installers_are_uniquely_identified(self):
        spec = self.read('PlexCastExplorer.iss')
        builder = self.read('build_installer_windows.ps1')
        gate = self.read('build_gate.py')
        self.assertIn('#ifndef DevBuildId', spec)
        self.assertIn('#error DevBuildId must be provided', spec)
        self.assertIn('#ifdef ReleaseBuild', spec)
        self.assertIn('AppVersion={#BuildVersion}', spec)
        self.assertIn('AppVerName={#BuildDisplayVersion}', spec)
        self.assertIn('OutputBaseFilename={#BuildFilename}', spec)
        self.assertIn('#define BuildVersion AppVersion + "-" + DevBuildId', spec)
        self.assertIn('#define BuildVersion AppVersion', spec)
        self.assertIn('yyyyMMdd-HHmmssfff', builder)
        self.assertIn("$appVersionMatch.Groups['version'].Value", builder)
        self.assertIn('rev-parse --verify --short=8 HEAD', builder)
        self.assertIn("'/DDevBuildId=' + $buildId", builder)
        self.assertIn("'/DReleaseBuild=1'", builder)
        self.assertIn('Stable Setup requires an approved clean dev or main checkout.', builder)
        self.assertIn("Invoke-LocalGate 'installer' -BuildId $buildId", builder)
        self.assertIn("def validate_build_id(", gate)

    def test_clean_stable_package_name_is_explicitly_opt_in(self):
        spec = self.read('PlexCastExplorer.iss')
        builder = self.read('build_installer_windows.ps1')
        self.assertIn('#define BuildFilename "PlexCastExplorer-Setup-" + AppVersion + "-win-x64"', spec)
        self.assertIn('OutputBaseFilename={#BuildFilename}', spec)
        self.assertIn('param([switch]$Release)', builder)
        self.assertIn('status --porcelain --untracked-files=normal', builder)
        self.assertIn('Stable Setup requires an approved clean dev or main checkout.', builder)

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
        self.assertIn("Get-CimInstance -ClassName Win32_Service", setup)
        self.assertIn("& sc.exe config $serviceName start= delayed-auto", setup)
        self.assertIn("& $wrapper start", setup)
        self.assertNotRegex(setup, r'(?m)^\s*&\s*\$wrapper\s+refresh\b')
        self.assertIn("$registeredAccount -notin", setup)
        self.assertIn("$serviceName = 'PlexCastExplorer'", setup)
        self.assertNotIn('Remove-Item -Recurse -Force $dataDir', setup + uninstall)
        self.assertIn('Stop-Service', uninstall)
        self.assertIn('Remove-NetFirewallRule', uninstall)

    def test_legacy_local_system_service_is_migrated_in_place(self):
        setup = self.read('installer/configure_service.ps1')
        self.assertIn("$registeredAccount -in @('LocalSystem', '.\\LocalSystem', 'NT AUTHORITY\\SYSTEM')", setup)
        self.assertIn('obj= "NT AUTHORITY\\LocalService" password= ""', setup)
        self.assertIn('Start-Process -FilePath $scPath -ArgumentList $scArguments', setup)
        self.assertIn('$migration.ExitCode -ne 0', setup)
        self.assertIn("Service registration missing after account migration.", setup)
        self.assertIn("$registeredAccount -notin @('NT AUTHORITY\\LocalService', 'LocalService')", setup)
        self.assertIn('Refusing to modify an unrecognized service identity.', setup)
        self.assertNotRegex(setup, r'(?m)^\s*&\s*\$wrapper\s+(uninstall|refresh)\b')

    def test_updates_are_consented_and_hash_verified(self):
        checker = self.read('installer/check_updates.ps1')
        self.assertIn('api.github.com/repos/', checker)
        self.assertIn('DownloadAndInstall', checker)
        self.assertIn('Get-FileHash', checker)
        self.assertIn("^sha256:", checker)
        self.assertIn("$answer -cne 'YES'", checker)
        self.assertIn('Start-Process -FilePath $installer -Verb RunAs', checker)

    def test_updater_recognizes_dev_build_version_assets(self):
        checker = self.read('installer/check_updates.ps1')
        self.assertIn('[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*', checker)
        pattern = r'^PlexCastExplorer-Setup-v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)?-win-x64\.exe$'
        self.assertRegex('PlexCastExplorer-Setup-1.0.0-dev-20261014-203512123-g23a496e7-win-x64.exe', pattern)
        self.assertRegex('PlexCastExplorer-Setup-1.0.0-win-x64.exe', pattern)

    def test_install_kit_has_build_pipeline(self):
        builder = self.read('build_installer_windows.ps1')
        self.assertIn("'-m','PyInstaller'", builder)
        self.assertIn('WinSW-x64.exe', builder)
        self.assertIn('ISCC.exe', builder)
        self.assertIn('PlexCastExplorer-Setup-$appVersion-$buildId-win-x64.exe', builder)
        self.assertEqual(
            re.search(r"^VERSION = '([^']+)'", self.read('app.py'), re.M).group(1),
            '1.0.0'
        )


if __name__ == '__main__':
    unittest.main()
