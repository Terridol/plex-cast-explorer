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
    build = read(root, 'build_installer_windows.ps1')
    runner = read(root, 'BUILD-INSTALLER.cmd')

    require(f'#define AppVersion "{version}"' in spec,
            'Installer version differs from app.py VERSION')
    require(f'PlexCastExplorer-Setup-{version}-win-x64.exe' in build,
            'Expected compiled installer filename/version differs from app.py')
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
    require("Get-CimInstance -ClassName Win32_Service" in service and
            '$registeredPath -ne $wrapper' in service and
            '$registered.StartName -notin' in service and
            '& sc.exe config $serviceName start= delayed-auto' in service and
            '& $wrapper start' in service,
            'Upgrades must validate the installed service and apply supported SCM settings')
    require('build_installer_windows.ps1' in runner,
            'BUILD-INSTALLER.cmd must use the gated local builder')
    require('build_gate.py' in build and "'source'" in build and
            "'exe'" in build and "'installer'" in build,
            'The build script must run all three mandatory gate stages')
    require('BUILD-EXE.cmd' in build and 'ISCC.exe' in build,
            'The build must compile both application and setup executable')
    return version


def checked_run(argv, label, *, timeout=180):
    print(f'\n[GATE] {label}', flush=True)
    result = subprocess.run(argv, cwd=ROOT, timeout=timeout, check=False)
    if result.returncode != 0:
        raise GateFailure(f'{label} FAILED (exit code {result.returncode})')


def source_gate():
    version = check_install_contract(ROOT)
    print(f'[GATE] Installer contract and version consistent: {version}', flush=True)
    checked_run([sys.executable, '-m', 'compileall', '-q', 'app.py', 'manage.py',
                 'build_gate.py', 'test_app.py', 'test_installer_spec.py',
                 'test_release_guardrails.py', 'test_remote_admin.py',
                 'test_security_images.py', 'test_build_gate.py'], 'Python syntax')
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


def installer_gate():
    version = check_install_contract(ROOT)
    out_dir = ROOT / 'output'
    exe = out_dir / f'PlexCastExplorer-Setup-{version}-win-x64.exe'
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
    args = parser.parse_args()
    try:
        {'source': source_gate, 'exe': executable_gate, 'installer': installer_gate}[args.stage]()
    except (GateFailure, OSError, subprocess.TimeoutExpired) as exc:
        print(f'\n[BUILD BLOCKED] {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())