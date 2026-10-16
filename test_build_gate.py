"""Mutation/regression tests: invalid installer edits MUST block local builds."""
import unittest
from unittest.mock import patch

import build_gate


class BuildGateRegressionTests(unittest.TestCase):
    def test_valid_baseline_contract(self):
        self.assertEqual(build_gate.check_install_contract(build_gate.ROOT),
                         build_gate.app_version(build_gate.ROOT))

    def assert_mutation_blocked(self, file, original, modified, occurrence=1):
        root = build_gate.ROOT
        path = root / file
        text = path.read_text(encoding='utf-8-sig')
        self.assertGreaterEqual(text.count(original), occurrence)
        with patch.object(build_gate, 'read') as read:
            def altered(root_arg, path_arg):
                result = (root_arg / path_arg).read_text(encoding='utf-8-sig')
                if path_arg != file:
                    return result
                parts = result.split(original)
                return (original.join(parts[:occurrence]) + modified +
                        original.join(parts[occurrence:]))
            read.side_effect = altered
            with self.assertRaises(build_gate.GateFailure):
                build_gate.check_install_contract(root)

    def test_missing_cpython_license_packaging_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     'Python-LICENSE.txt', 'missing-python-license.txt')

    def test_powershell_native_argument_quoting_cannot_break_license_check(self):
        # Older code passed a quoted filename through Windows PowerShell 5.1
        # to py.exe, which stripped the quotes and caused NameError.
        self.assert_mutation_blocked(
            'build_installer_windows.ps1',
            "-c 'import sys; print(sys.base_prefix)'",
            "-c 'import pathlib,sys; print(pathlib.Path(sys.base_prefix) / \"LICENSE.txt\")'"
        )

    def test_missing_output_cleanup_is_fatal(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     'Remove-Item -Force -Recurse -ErrorAction Stop',
                                     'Write-Host "Skipping output cleanup"')

    def test_output_cleanup_cannot_change_target_directory(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     "$outputDir = Join-Path $root 'output'",
                                     "$outputDir = Join-Path $root 'dist'")

    def test_output_cleanup_must_reject_reparse_points(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     'Refusing to clear output: junction or symbolic link found',
                                     'Following output junctions is allowed')

    def test_output_cleanup_must_verify_empty_result(self):
        self.assert_mutation_blocked(
            'build_installer_windows.ps1',
            'Output cleanup failed; refusing to write an installer into a nonempty output folder.',
            'Output cleanup failure ignored.'
        )

    def test_plex_actor_portrait_sync_cannot_be_silently_skipped(self):
        self.assert_mutation_blocked('app.py',
                                     'errors += cache_plex_portraits()',
                                     'errors += 0  # skip portrait cache')

    def test_custom_scraper_proxy_must_require_public_https_destination(self):
        self.assert_mutation_blocked('app.py',
                                     'ipaddress.ip_address(result[4][0]).is_global',
                                     'True  # skip public IP validation')

    def test_custom_scraper_proxy_must_not_accept_arbitrary_input(self):
        self.assert_mutation_blocked('app.py',
                                     'raw = plex_transcoded_image(thumb)',
                                     "raise ValueError('Unknown artwork source')")

    def test_plex_portrait_http_errors_cannot_hide_status_code(self):
        self.assert_mutation_blocked('app.py',
                                     "if code in (404, 410):",
                                     "if code in ():  # no missing-art handling")

    def test_plex_cdn_errors_cannot_stop_all_other_sources(self):
        self.assert_mutation_blocked(
            'app.py',
            'groups.setdefault(plex_portrait_source_group(thumb), []).append(thumb)',
            "groups.setdefault(('all', ''), []).append(thumb)")

    def test_plex_failed_source_skipped_count_is_required(self):
        # All three calls are safety-critical: per-image update, per-origin
        # breaker and global stop. A string-contains gate used to miss the
        # first mutation because the other two calls remained unchanged.
        for occurrence in (1, 2, 3):
            with self.subTest(report_path=occurrence):
                self.assert_mutation_blocked(
                    'app.py', 'portrait_skipped=skipped',
                    'portrait_skipped=0', occurrence=occurrence)

    def test_plex_portrait_live_failure_counts_required(self):
        self.assert_mutation_blocked('app.py',
                                     "errors=baseline_errors + failures",
                                     "errors=baseline_errors")

    def test_plex_actor_cache_must_remain_size_bounded(self):
        self.assert_mutation_blocked('app.py',
                                     'MAX_PLEX_IMAGE_BYTES = 4_000_000',
                                     'MAX_PLEX_IMAGE_BYTES = 0')

    def test_custom_agent_bundle_uri_support_is_required(self):
        self.assert_mutation_blocked(
            'app.py', "'/file?' + urlencode({'url': thumb})",
            "'/missing?' + urlencode({'url': thumb})")

    def test_custom_agent_person_metadata_is_required(self):
        self.assert_mutation_blocked(
            'app.py', 'errors += resolve_plex_actor_refs()',
            'errors += 0  # disabled reference lookups')

    def test_missing_project_notice_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                     'Source: "NOTICE"; DestDir: "{app}"',
                                     'Source: "NOT_A_NOTICE"; DestDir: "{app}"')

    def test_version_drift_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    '#define AppVersion "1.0.0"',
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
                                     "$installed = '1.0.0'",
                                     "$installed = '0.4.6-beta'")

    def test_service_version_mismatch_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     "$ExpectedVersion = '1.0.0'",
                                     "$ExpectedVersion = '0.4.6-beta'")

    def test_dev_build_id_has_strict_format(self):
        build_gate.validate_build_id('dev-20261014-203512123-g23a496e7')
        build_gate.validate_build_id('dev-20261014-203512123-s01234567')
        for bad in ('', '1.0.0', 'dev-20261014-g23a496e7',
                    'dev-20261014-203512123-nohash', '../malicious'):
            with self.subTest(bad=bad), self.assertRaises(build_gate.GateFailure):
                build_gate.validate_build_id(bad)

    def test_missing_dev_build_display_version_is_fatal(self):
        self.assert_mutation_blocked('PlexCastExplorer.iss',
                                    '#define BuildVersion AppVersion + "-" + DevBuildId',
                                    '#define BuildVersion AppVersion')

    def test_stable_release_requires_main_and_semver(self):
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     'Stable Setup requires an approved clean dev or main checkout.',
                                     'Stable Setup can be built on dev.')
        self.assert_mutation_blocked('build_installer_windows.ps1',
                                     "'/DReleaseBuild=1'", "'/DDevBuildId=' + $buildId")

    def test_prerelease_cannot_pass_stable_installer_gate(self):
        self.assertEqual(build_gate.validate_release_version('1.0.0'), '1.0.0')
        for bad in ('1.0.0-rc.1', '1.0.0-beta', '1.0.0+dirty', '', '1.0'):
            with self.subTest(version=bad), self.assertRaises(build_gate.GateFailure):
                build_gate.validate_release_version(bad)

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

    def test_missing_legacy_service_identity_migration_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     "'LocalSystem', '.\\LocalSystem', 'NT AUTHORITY\\SYSTEM'",
                                     "'UnsupportedLegacyAccount'")

    def test_migration_identity_destination_drift_is_fatal(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     'obj= "NT AUTHORITY\\LocalService" password= ""',
                                     'obj= "LocalSystem" password= ""')

    def test_migration_exit_code_must_be_checked(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     '$migration.ExitCode -ne 0',
                                     '$false')

    def test_custom_service_account_must_still_be_rejected(self):
        self.assert_mutation_blocked('installer/configure_service.ps1',
                                     'Refusing to modify an unrecognized service identity.',
                                     'Accepting any service identity.')

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

    def test_missing_post_migration_service_verification_is_fatal(self):
        # Distinct from the original service-registration lookup: an upgrade
        # must independently re-read SCM after changing the account.
        self.assert_mutation_blocked(
            'installer/configure_service.ps1',
            '        $registered = Get-CimInstance -ClassName Win32_Service',
            '        $registered = Get-Service -Name $serviceName'
        )

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