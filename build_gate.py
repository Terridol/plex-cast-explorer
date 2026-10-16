"""Mandatory local build gate for Plex Cast Explorer.

Stages run in order: source -> exe -> installer. No GitHub or remote CI is used.
This does NOT replace an actual Windows service installation test on an isolated VM.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
import hashlib

ROOT = Path(__file__).resolve().parent
SERVICE_RULE = 'PlexCastExplorer-Inbound-Private'


class GateFailure(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise GateFailure(reason)


def read(root: Path, path: str) -> str:
    try:
        return (root / path).read_text(encoding='utf-8-sig')
    except OSError as exc:
        raise GateFailure(f'Missing required build file {path}: {exc}') from exc


def app_version(root: Path) -> str:
    match = re.search(r"(?m)^VERSION\s*=\s*'([^']+)'", read(root, 'app.py'))
    require(match is not None, 'app.py must declare a VERSION string')
    return match.group(1)


def check_install_contract(root: Path) -> str:
    """Reject version drift, accidentally disabled gates and unsafe installer changes."""
    version = app_version(root)
    spec = read(root, 'PlexCastExplorer.iss')
    service = read(root, 'installer/configure_service.ps1')
    winsw_license = read(root, 'legal/WinSW-LICENSE.txt')
    build = read(root, 'build_installer_windows.ps1')
    runner = read(root, 'BUILD-INSTALLER.cmd')
    updater = read(root, 'installer/check_updates.ps1')

    require("if path == '/privacy':" in read(root, 'app.py') and
            "href=\"/privacy\"" in read(root, 'static/login.html') and
            "href=\"/privacy\"" in read(root, 'static/index.html') and
            'Plex Cast Explorer — Privacy & Legal' in read(root, 'static/privacy.html'),
            'A public privacy/legal notice must be accessible before gallery authentication')
    require('Source: "NOTICE"; DestDir: "{app}"' in spec and
            "bundledLicenses = Join-Path $root 'dist\\PlexCastExplorer\\licenses'" in build and
            'Python-LICENSE.txt' in build and
            'runtimeLicense' in build,
            'Windows installer must include CPython runtime license and project NOTICE')
    # PowerShell 5.1 passes quoted Python source to native commands
    # differently from Python/Unix shells. Nested "LICENSE.txt" quotes
    # previously disappeared, producing NameError after the EXE smoke gate.
    require("-c 'import sys; print(sys.base_prefix)'" in build and
            "$pythonInstallRoot = $pythonPrefix[0].Trim()" in build and
            "Join-Path -Path $pythonInstallRoot -ChildPath 'LICENSE.txt'" in build and
            'Copy-Item -LiteralPath $runtimeLicense -Destination' in build,
            'CPython license discovery must avoid nested quotes in native Python arguments')
    # Plex sync must acquire the actor portraits advertised by Role.thumb,
    # not merely record their URL and leave every gallery request to fetch it.
    # Existing manual artwork must retain priority over Plex's local cache.
    app_source = read(root, 'app.py')
    require("PLEX_PORTRAIT_DIR = ROOT / 'plex-portraits'" in app_source and
            'def cache_plex_portraits()' in app_source and
            'errors += cache_plex_portraits()' in app_source and
            'return cached_plex_portrait(thumb)' in app_source and
            'MAX_PLEX_IMAGE_BYTES = 4_000_000' in app_source and
            'def public_custom_plex_thumb(url: str) -> bool:' in app_source and
            'def plex_transcoded_image(url: str) -> bytes:' in app_source and
            "'/photo/:/transcode?' + urlencode" in app_source and
            'socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)' in app_source and
            "ipaddress.ip_address(result[4][0]).is_global" in app_source and
            "'url': url, 'width': 300, 'height': 450, 'format': 'jpeg'" in app_source and
            'raw = plex_transcoded_image(thumb)' in app_source and
            'NOT EXISTS (' in app_source and
            'plex-portraits/' in read(root, '.gitignore'),
            'Plex actor images must be safely fetched via Plex for both built-in and custom agents')
    # The status endpoint must show image failures *during* a 50k+ portrait
    # scan. HTTP 404/410 is missing artwork; 401/403/429/5xx is diagnostic
    # and must not hide its numerical status or expose a URL/token.
    require("except HTTPError as exc:" in app_source and
            "if code in (404, 410):" in app_source and
            "portrait_missing=missing" in app_source and
            "errors=baseline_errors + failures" in app_source and
            "HTTP 429 (rate limited)" in app_source and
            "portrait_downloaded=downloaded" in app_source and
            'def plex_portrait_source_group(thumb: str)' in app_source and
            "MAX_PLEX_SOURCE_DENIALS = 10" in app_source and
            "groups.setdefault(plex_portrait_source_group(thumb), []).append(thumb)" in app_source and
            "portrait_skipped=skipped" in app_source and
            "current=attempted" in app_source and
            "' skipped due to source errors'" in read(root, 'static/app.js') and
            "def plex_portrait_source_label(thumb: str) -> str:" in app_source and
            "'portraits'" in read(root, 'static/app.js') and
            "hasImageSummary" in read(root, 'static/app.js'),
            'Portrait sync must distinguish missing art, authentication and rate-limit errors with live counts')
    require('CREATE TABLE IF NOT EXISTS actor_plex_refs' in app_source and
            'def plex_role_thumb(role, rating_key:' in app_source and
            'def plex_role_metadata_path(role)' in app_source and
            'def resolve_plex_actor_refs()' in app_source and
            'errors += resolve_plex_actor_refs()' in app_source and
            "'/file?' + urlencode({'url': thumb})" in app_source and
            'plex_transcoded_image(thumb)' in app_source,
            'Custom Plex actor images require bundle, person-reference, and proxy handling')
    require('Name: "tmdb"' in spec and
            "WizardIsTaskSelected('tmdb')" in spec and
            "if ($EnableTMDB -eq 1)" in service and
            "CAST_EXPLORER_ENABLE_TMDB" in read(root, 'app.py') and
            "if keys['theporndb'] and not found:" in read(root, 'app.py') and
            "if keys['theporndb'] and not results:" in read(root, 'app.py') and
            "retry_unmatched_enrichment" in read(root, 'app.py') and
            "enrichRetryUnmatched" in read(root, 'static/app.js') and
            "This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB." in read(root, 'static/privacy.html') and
            "blue_short-8e7b30" in read(root, 'static/index.html'),
            'GA 1.0 must preserve authorized TMDB-first lookup, TPDB fallback and TMDB attribution')
    require('MIT License' in winsw_license and
            'Kohsuke Kawaguchi' in winsw_license and
            'Source: "legal\\WinSW-LICENSE.txt"; DestDir: "{app}\\licenses"' in spec,
            'Bundled WinSW must include its upstream MIT license notice')
    require(f'#define AppVersion "{version}"' in spec,
            'Installer version differs from app.py VERSION')
    # Validate the actual meaning of the PowerShell expression. PowerShell
    # strings preserve backslashes, so a doubled \s silently breaks matching.
    extraction = re.search(
        r'(?m)^\$appVersionMatch = \[regex\]::Match\(\$appSource, "([^"\r\n]+)"\)\s*$',
        build,
    )
    require(extraction is not None, 'Missing or altered PowerShell version parser')
    version_pattern = extraction.group(1).replace('(?<version>', '(?P<version>')
    try:
        actual_version = re.search(version_pattern, read(root, 'app.py'))
    except re.error as exc:
        raise GateFailure(f'Invalid PowerShell version regex: {exc}') from exc
    require(actual_version is not None and
            actual_version.group('version') == version,
            'PowerShell version regex cannot extract app.py VERSION (check backslash escaping)')
    require(build.index('$appVersionMatch = [regex]::Match') <
            build.index("Invoke-Python @('-c'"),
            'App version must be parsed before dependency downloads and EXE compilation')
    require(f"$installed = '{version}'" in updater,
            'Updater installed-version constant must match app.py VERSION')
    require(f"$ExpectedVersion = '{version}'" in service,
            'Service expected-version default must match app.py VERSION')
    require('#ifndef DevBuildId' in spec and '#error DevBuildId must be provided' in spec,
            'Development installer must require a build ID at compilation')
    require('AppVersion={#BuildVersion}' in spec and
            'AppVerName={#BuildDisplayVersion}' in spec and
            'OutputBaseFilename={#BuildFilename}' in spec and
            '#ifdef ReleaseBuild' in spec and
            '#define BuildVersion AppVersion' in spec and
            '#define BuildVersion AppVersion + "-" + DevBuildId' in spec and
            '#define BuildFilename "PlexCastExplorer-Setup-" + AppVersion + "-win-x64"' in spec and
            '#define BuildFilename "PlexCastExplorer-Setup-" + AppVersion + "-" + DevBuildId + "-win-x64"' in spec,
            'Setup must support separate stable and uniquely identified development artifacts')
    # Regression: a string replacement involving the regex end anchor ('$')
    # once duplicated the entire installer tail inside a PowerShell string.
    # This structural check protects non-Windows source reviews as well as
    # the Windows AST parsing performed before build_installer_windows.ps1 runs.
    require(build.count('function Get-ISCC {') == 1 and
            build.count('# Delete an old artifact first:') == 1 and
            build.count("Invoke-LocalGate 'installer' -BuildId $buildId") == 1 and
            build.count("Write-Host 'Installer not yet smoke-tested;") == 1 and
            "$gitHead[-1] -match '^[0-9a-fA-F]{8}$'" in build and
            "$buildId -notmatch '^dev-[0-9]{8}-[0-9]{9}-[gs][0-9a-f]{8}$'" in build,
            'Windows build script has duplicated sections or corrupt build-ID regex')
    # Each build replaces the output directory contents, instead of accumulating
    # dev IDs or leaving a stale release installer behind. Keep cleanup inside
    # the repository and reject junctions/symlinks before recursive deletion.
    require("$outputDir = Join-Path $root 'output'" in build and
            "Get-ChildItem -LiteralPath $outputDir -Recurse -Force -ErrorAction Stop" in build and
            "Refusing to clear output: junction or symbolic link found" in build and
            "Get-ChildItem -LiteralPath $outputDir -Force -ErrorAction Stop |\n        Remove-Item -Force -Recurse -ErrorAction Stop" in build and
            "Output cleanup failed; refusing to write an installer into a nonempty output folder." in build and
            "Keep older build IDs in the output folder" not in build and
            0 <= build.find("$outputDir = Join-Path $root 'output'") <
                 build.find('Write-Host "Compiling Setup.exe'),
            'Build must safely empty only repo/output before every installer compile')
    require('PlexCastExplorer-Setup-$appVersion-$buildId-win-x64.exe' in build and
            "$appVersionMatch.Groups['version'].Value" in build and
            "'/DDevBuildId=' + $buildId" in build and
            "Invoke-LocalGate 'installer' -BuildId $buildId" in build and
            'yyyyMMdd-HHmmssfff' in build and 'rev-parse --verify --short=8 HEAD' in build,
            'Windows build script must derive the app version and embed a unique build ID in Setup and validation')
    require("param([switch]$Release)" in build and
            "'/DReleaseBuild=1'" in build and
            'Stable Setup requires an approved clean dev or main checkout.' in build and
            "Stable Setup requires a final MAJOR.MINOR.PATCH version" in build and
            'PlexCastExplorer-Setup-$appVersion-win-x64.exe' in build,
            'Stable Setup builds must require a final version and approved main checkout')
    require('AppId={{974DC3BB-C0AD-46E4-A920-053E710D988C}' in spec,
            'Product AppId changed: this would break in-place upgrades')
    require('UsePreviousAppDir=yes' in spec and 'UsePreviousTasks=yes' in spec,
            'Installer must preserve previous directory and tasks')
    require('function PrepareToInstall(' in spec and 'Stop-Service' in spec,
            'Installer must stop previous service before replacing executable files')
    require('procedure CurStepChanged(CurStep: TSetupStep);' in spec and
            'CurStep <> ssPostInstall' in spec, 'Installer must start service before Finish screen')
    require('ewWaitUntilTerminated' in spec and 'if ExitCode <> 0 then' in spec and
            'RaiseException(' in spec and '-ExpectedVersion ' in spec,
            'Installer must block Finish when service startup/readiness fails')
    require('installer-last-error.txt' in service and
            'installer-error-details.log' in service and
            'trap {' in service and 'exit 1' in service and
            'LoadStringFromFile(FailurePath, FailureRaw)' in spec and
            'FailureRaw: AnsiString' in spec and
            'FailureReason := Trim(FailureRaw)' in spec,
            'Installer must record and display the real PowerShell startup failure')
    run_section = spec.split('[Run]', 1)[-1].split('[UninstallRun]', 1)[0]
    require('configure_service.ps1' not in run_section,
            'Service start must not be hidden as a normal [Run] action')
    require('WaitForStatus(\'Running\'' in service and
            'http://127.0.0.1:$Port/api/config' in service and
            '$health.version -eq $ExpectedVersion' in service and
            'if (-not $ready)' in service,
            'Service readiness must validate HTTP response and exact app version')
    require('-Profile Private -RemoteAddress $remote' in service and
            "$remote = @('LocalSubnet') + $addresses" in service and
            SERVICE_RULE in service and '-Profile Any' not in service and
            '-Profile Public' not in service,
            'Firewall must be private and scoped to approved LAN/VPN clients')
    require("'cast_explorer.db-wal'" in service and
            'Remove-Item -Recurse -Force $dataDir' not in service,
            'Service upgrades must preserve runtime data and take a backup')
    # WinSW 2.12 only implements install/uninstall/start/stop/restart/status.
    # This exact unsupported command broke upgrades on a real Windows host.
    require(not re.search(r'(?m)^\s*&\s*\$wrapper\s+refresh\b', service, re.I),
            'Unsupported WinSW v2 refresh command would stop the service during upgrade')
    # Require verification before AND after changing the service account.
    # A single string-presence check became insufficient once a second
    # Get-CimInstance call was added by the legacy-account migration.
    require(service.count('Get-CimInstance -ClassName Win32_Service') == 2,
            'Existing service registration must be checked before and after migration')
    require("Get-CimInstance -ClassName Win32_Service" in service and
            '$registeredPath -ne $wrapper' in service and
            '$registeredAccount -notin' in service and
            '& sc.exe config $serviceName start= delayed-auto' in service and
            '& $wrapper start' in service,
            'Upgrades must validate the installed service and apply supported SCM settings')
    # Historical Windows installations can have SCM identity LocalSystem,
    # whereas the new service XML expects LocalService. Migrate only the
    # known legacy built-in identity, and validate the SCM result before start.
    require("$registeredAccount -in @('LocalSystem', '.\\LocalSystem', 'NT AUTHORITY\\SYSTEM')" in service and
            'Start-Process -FilePath $scPath' in service and
            'obj= "NT AUTHORITY\\LocalService" password= ""' in service and
            '$migration.ExitCode -ne 0' in service and
            'Service registration missing after account migration.' in service and
            '$registeredAccount -notin' in service and
            'Refusing to modify an unrecognized service identity.' in service,
            'Legacy LocalSystem services must migrate in place without accepting custom identities')
    # Regression: a regular-expression edit once swallowed the closing quote
    # and duplicated the update checker tail. That corruption passed basic
    # Python tests but failed Windows PowerShell parsing before installation.
    require(updater.count('Start-Process -FilePath $installer -Verb RunAs -Wait') == 1 and
            updater.count('$asset = @($release.assets) | Where-Object') == 1 and
            updater.count('# Release-asset digest comes from GitHub') == 1,
            'Updater contains duplicated release/download sections')
    asset_lines = [line for line in updater.splitlines()
                   if '$asset = @($release.assets) | Where-Object' in line]
    require(len(asset_lines) == 1 and
            "win-x64\\.exe$' } | Select-Object -First 1" in asset_lines[0] and
            '[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*' in asset_lines[0],
            'Updater release-asset filename regex is truncated or missing its closing quote')
    require('scripts\\validate_powershell.ps1' in runner and
            'if errorlevel 1 (' in runner and
            runner.index('scripts\\validate_powershell.ps1') < runner.index('build_installer_windows.ps1'),
            'Windows builder must parse ALL PowerShell scripts before launching the build')
    require('build_installer_windows.ps1' in runner,
            'BUILD-INSTALLER.cmd must use the gated local builder')
    require('build_gate.py' in build and "'source'" in build and
            "'exe'" in build and "'installer'" in build,
            'The build script must run all three mandatory gate stages')
    require("'-m','PyInstaller'" in build and 'ISCC.exe' in build and
            "Invoke-LocalGate 'exe'" in build,
            'The one supported build orchestrator must compile and smoke-test both application and Setup')
    return version


def checked_run(argv, label, *, timeout=180):
    print(f'\n[GATE] {label}', flush=True)
    result = subprocess.run(argv, cwd=ROOT, timeout=timeout, check=False)
    if result.returncode != 0:
        raise GateFailure(f'{label} FAILED (exit code {result.returncode})')


def source_gate():
    version = check_install_contract(ROOT)
    print(f'[GATE] Installer contract and version consistent: {version}', flush=True)
    checked_run([sys.executable, '-m', 'compileall', '-q', 'app.py',
                 'build_gate.py', 'test_app.py', 'test_installer_spec.py',
                 'test_release_guardrails.py', 'test_remote_admin.py',
                 'test_security_images.py', 'test_build_gate.py',
                 'test_repository_layout.py'], 'Python syntax')
    checked_run([sys.executable, '-m', 'unittest', 'discover', '-s', '.',
                 '-p', 'test_*.py', '-v'], 'Regression tests', timeout=300)

    if os.name == 'nt':
        powershell = shutil.which('powershell.exe')
        require(powershell, 'Windows PowerShell not found; cannot parse installer scripts')
        checked_run([powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                     'Bypass', '-File', str(ROOT / 'scripts' / 'validate_powershell.ps1')],
                    'PowerShell parse validation')
    else:
        print('[GATE] PowerShell parser skipped (requires Windows host).')
    node = shutil.which('node') or shutil.which('node.exe')
    if node:
        checked_run([node, '--check', str(ROOT / 'static' / 'app.js')], 'JavaScript syntax')
    else:
        print('[GATE] WARNING: Node.js unavailable; JavaScript syntax not checked. '
              'The Windows installer regression and EXE launch tests are still mandatory.')
    print('\n[GATE PASS] Source validation succeeded.', flush=True)


def request(opener, uri, *, headers=None, method='GET', data=None):
    req = Request(uri, headers=headers or {}, method=method, data=data)
    with opener.open(req, timeout=2) as response:
        return response.status, response.read()


def get_ephemeral_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def executable_gate():
    exe = ROOT / 'dist' / 'PlexCastExplorer' / ('PlexCastExplorer.exe' if os.name == 'nt' else 'PlexCastExplorer')
    require(exe.is_file(), f'Built application executable missing: {exe}')
    version = app_version(ROOT)
    with tempfile.TemporaryDirectory(prefix='plex-cast-build-gate-') as tmp:
        env = dict(os.environ)
        port = get_ephemeral_port()
        env.update({
            'CAST_EXPLORER_DATA_DIR': tmp,
            'CAST_EXPLORER_HOST': '127.0.0.1',
            'CAST_EXPLORER_PORT': str(port),
            'CAST_EXPLORER_SYNC_HOURS': '9999',
            'CAST_EXPLORER_ENABLE_TMDB': '0',
            'CAST_EXPLORER_ENABLE_WIKIMEDIA': '0',
            'CAST_EXPLORER_REMOTE_ADMIN_CIDRS': '',
        })
        check = subprocess.run([str(exe), '--version'], env=env, cwd=ROOT,
                               capture_output=True, text=True, timeout=20)
        require(check.returncode == 0 and check.stdout.strip() == version,
                f'EXE --version failed: expected {version!r}, got {check.stdout!r} ({check.stderr[-500:]})')
        proc = subprocess.Popen([str(exe)], cwd=ROOT, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        opener = build_opener(ProxyHandler({}))
        base = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + 40
        try:
            while True:
                require(proc.poll() is None,
                        'Built EXE terminated during launch; service installation would fail')
                try:
                    status, data = request(opener, base + '/api/config')
                    if status == 200:
                        details = json.loads(data)
                        if details.get('version') == version and details.get('admin') is True:
                            break
                except (URLError, OSError, ValueError):
                    pass
                if time.monotonic() >= deadline:
                    raise GateFailure(f'Built EXE did not become ready at {base} in 40 seconds')
                time.sleep(.25)
            print(f'[GATE] EXE returned expected version {version} on isolated localhost port {port}', flush=True)
            status, body = request(opener, base + '/')
            require(status == 200 and b'<html' in body.lower(), 'Packaged HTML frontend missing')
            status, body = request(opener, base + '/static/app.js')
            require(status == 200 and len(body) > 100, 'Packaged JavaScript frontend missing')
            status, body = request(opener, base + '/api/session')
            require(status == 200 and json.loads(body).get('admin') is True,
                    'Local administration not recognized')
            try:
                request(opener, base + '/api/config', headers={'Host': f'untrusted.example:{port}'})
                raise GateFailure('Host header check failed open')
            except HTTPError as exc:
                require(exc.code == 400, f'Untrusted host should yield HTTP 400, got {exc.code}')
            try:
                request(opener, base + '/api/login', method='POST', data=b'{}',
                        headers={'Content-Type': 'text/plain'})
                raise GateFailure('CSRF content type validation failed open')
            except HTTPError as exc:
                require(exc.code == 415, f'Text/plain POST should yield HTTP 415, got {exc.code}')
            require((Path(tmp) / 'cast_explorer.db').is_file(), 'Isolated database not initialized')
            print('[GATE PASS] Packaged EXE launched; API, static UI, version, Host/CSRF checks passed.', flush=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def validate_release_version(version: str) -> str:
    """Require an explicit stable semver; reject prerelease/build suffixes."""
    require(bool(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version or '')),
            'Stable installer cannot be produced from a prerelease source version')
    return version


def validate_build_id(build_id: str) -> str:
    require(bool(re.fullmatch(r'dev-[0-9]{8}-[0-9]{9}-[gs][0-9a-f]{8}', build_id or '')),
            'Installer gate requires a valid unique dev build ID')
    return build_id


def installer_gate(build_id: str):
    version = check_install_contract(ROOT)
    out_dir = ROOT / 'output'
    if build_id == 'release':
        validate_release_version(version)
        exe = out_dir / f'PlexCastExplorer-Setup-{version}-win-x64.exe'
    else:
        build_id = validate_build_id(build_id)
        exe = out_dir / f'PlexCastExplorer-Setup-{version}-{build_id}-win-x64.exe'
    license_file = ROOT / 'dist' / 'PlexCastExplorer' / 'licenses' / 'Python-LICENSE.txt'
    require(license_file.is_file() and license_file.stat().st_size > 256,
            'Bundled CPython license is missing or truncated')
    require(exe.is_file(), f'Expected installer is missing: {exe}')
    size = exe.stat().st_size
    require(size >= 1024 * 1024, f'Installer looks truncated: {size} bytes')
    with exe.open('rb') as f:
        require(f.read(2) == b'MZ', 'Installer does not have a Windows PE header')
    expected = '05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da'
    wrapper = ROOT / 'installer-assets' / 'WinSW-x64.exe'
    require(wrapper.is_file(), 'Pinned service wrapper missing from build inputs')
    require(hashlib.sha256(wrapper.read_bytes()).hexdigest() == expected,
            'Service wrapper checksum mismatch')
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    checksum = exe.with_suffix('.exe.sha256')
    require(checksum.is_file(), 'Installer SHA-256 sidecar missing')
    require(checksum.read_text(encoding='ascii').strip() == f'{sha}  {exe.name}',
            'Installer checksum is incorrect or stale')
    print(f'[GATE PASS] Windows Setup artifact checked: {exe.name} ({size:,} bytes) SHA256 {sha}', flush=True)
    print('[GATE] IMPORTANT: actual Windows service installation/upgrade on a disposable '
          'VM is a separate mandatory RELEASE gate; artifact build alone is not an install test.', flush=True)


def main():
    parser = argparse.ArgumentParser(description='Plex Cast Explorer build regression gate')
    parser.add_argument('stage', choices=['source', 'exe', 'installer'])
    parser.add_argument('--build-id', default='', help='Exact dev build ID for the compiled installer')
    args = parser.parse_args()
    try:
        if args.stage == 'installer':
            installer_gate(args.build_id)
        else:
            {'source': source_gate, 'exe': executable_gate}[args.stage]()
    except (GateFailure, OSError, subprocess.TimeoutExpired) as exc:
        print(f'\n[BUILD BLOCKED] {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())