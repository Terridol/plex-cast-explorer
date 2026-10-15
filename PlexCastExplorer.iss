#define AppName "Plex Cast Explorer"
#define AppVersion "0.4.7-beta"
#define Publisher "Terridol"
#define AppExe "PlexCastExplorer.exe"

[Setup]
; Stable application identity: retain across all future versions for reliable upgrades.
AppId={{974DC3BB-C0AD-46E4-A920-053E710D988C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL=https://github.com/Terridol/plex-cast-explorer
AppSupportURL=https://github.com/Terridol/plex-cast-explorer/issues
AppUpdatesURL=https://github.com/Terridol/plex-cast-explorer/releases
DefaultDirName={autopf}\PlexCastExplorer
DefaultGroupName=Plex Cast Explorer
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=PlexCastExplorer-Setup-{#AppVersion}-win-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\PlexCastExplorer.exe
ChangesEnvironment=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
CloseApplications=no
RestartApplications=no
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "firewall"; Description: "Add inbound Windows Firewall rule (Private network, local subnet only)"; GroupDescription: "Network access:"
Name: "tmdb"; Description: "Enable TMDB lookup (only if your use meets TMDB's API and attribution terms)"; GroupDescription: "Optional providers:"; Flags: unchecked
Name: "remoteadmin"; Description: "Enable remote administration for specified VPN client CIDRs"; GroupDescription: "Security:"; Flags: unchecked
Name: "beta"; Description: "Offer beta releases when checking for updates"; GroupDescription: "Updates:"; Flags: unchecked
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
; Compiled one-folder PyInstaller output (includes all Python runtime dependencies).
Source: "dist\PlexCastExplorer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer-assets\WinSW-x64.exe"; DestDir: "{app}"; DestName: "PlexCastExplorerService.exe"; Flags: ignoreversion
Source: "installer\configure_service.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\uninstall_cleanup.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\configure_password.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\check_updates.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Plex Cast Explorer"; Filename: "http://127.0.0.1:{code:GetPort}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 220
Name: "{group}\Check for Updates"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -NoExit -File ""{app}\check_updates.ps1"""; WorkingDir: "{app}"
Name: "{group}\Set Gallery Password"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -NoExit -File ""{app}\configure_password.ps1"""; WorkingDir: "{app}"
Name: "{group}\Set Remote Admin Password"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -NoExit -File ""{app}\configure_password.ps1"" -Admin"; WorkingDir: "{app}"
Name: "{group}\Uninstall Plex Cast Explorer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Plex Cast Explorer"; Filename: "http://127.0.0.1:{code:GetPort}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 220; Tasks: desktopicon

[Run]
; The service is started and health-checked in CurStepChanged(ssPostInstall),
; before the Finish screen. Errors prevent a false 'successful' install.
Filename: "http://127.0.0.1:{code:GetPort}"; Description: "Open Plex Cast Explorer"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall_cleanup.ps1"""; Flags: runhidden waituntilterminated; RunOnceId: "PlexCastExplorerServiceCleanup"

[Code]
var
  NetworkPage: TInputQueryWizardPage;

function GetPort(Param: String): String;
begin
  if NetworkPage <> nil then Result := Trim(NetworkPage.Values[0]) else Result := '8765';
end;

function GetRemoteCIDRs(Param: String): String;
begin
  Result := '';
  if (NetworkPage <> nil) and WizardIsTaskSelected('remoteadmin') then
    Result := Trim(NetworkPage.Values[1]);
end;

function GetTMDB(Param: String): String;
begin
  if WizardIsTaskSelected('tmdb') then Result := '1' else Result := '0';
end;

function GetFirewall(Param: String): String;
begin
  if WizardIsTaskSelected('firewall') then Result := '1' else Result := '0';
end;

function GetBeta(Param: String): String;
begin
  if WizardIsTaskSelected('beta') then Result := '1' else Result := '0';
end;

procedure InitializeWizard();
var
  Ini: String;
begin
  NetworkPage := CreateInputQueryPage(wpSelectTasks,
    'Service and VPN configuration',
    'Choose the HTTP listening port and (optionally) VPN client addresses.',
    'The app is NOT designed for public Internet exposure. Firewall access is limited to the Private profile. For remote administration, enable the VPN option on the previous page and enter exact client addresses (/32 or /128 recommended).');
  NetworkPage.Add('Listening port (default 8765):', False);
  NetworkPage.Add('Allowed VPN client CIDRs (comma-separated, if enabled):', False);
  Ini := ExpandConstant('{commonappdata}\PlexCastExplorer\installer-options.ini');
  NetworkPage.Values[0] := GetIniString('Service','Port','8765',Ini);
  NetworkPage.Values[1] := GetIniString('Service','RemoteAdminCIDRs','',Ini);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Port: Integer;
  CIDRs: String;
begin
  Result := True;
  if CurPageID = NetworkPage.ID then begin
    Port := StrToIntDef(Trim(NetworkPage.Values[0]), -1);
    if (Port < 1024) or (Port > 65535) then begin
      MsgBox('Enter a listening port between 1024 and 65535.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    CIDRs := Trim(NetworkPage.Values[1]);
    if WizardIsTaskSelected('remoteadmin') and (CIDRs = '') then begin
      MsgBox('Enter at least one VPN client CIDR, such as 10.20.30.4/32, or disable remote administration.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if (Pos('"', CIDRs) > 0) or (Pos(';', CIDRs) > 0) or (Pos('&', CIDRs) > 0) or (Pos('|', CIDRs) > 0) then begin
      MsgBox('VPN addresses may only contain numeric IP addresses, / masks, and commas.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  ExecOk: Boolean;
  Args: String;
begin
  Result := '';
  // Do not attempt to replace a running PyInstaller executable or wrapper.
  Args := '-NoProfile -ExecutionPolicy Bypass -Command "try { $s = Get-Service -Name PlexCastExplorer -ErrorAction SilentlyContinue; if ($s -and $s.Status -ne ''Stopped'') { Stop-Service -Name PlexCastExplorer -Force -ErrorAction Stop; (Get-Service -Name PlexCastExplorer).WaitForStatus(''Stopped'', [TimeSpan]::FromSeconds(30)) }; exit 0 } catch { exit 1 }"';
  ExecOk := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Args,
                 '', SW_HIDE, ewWaitUntilTerminated, ExitCode);
  if (not ExecOk) or (ExitCode <> 0) then
    Result := 'Unable to stop the existing PlexCastExplorer service. Close the app and retry.';
end;

 
// Installation is not complete until the expected application version responds.
procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
  Args: String;
  Started: Boolean;
  FailureReason: String;
  FailurePath: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  WizardForm.StatusLabel.Caption := 'Starting Plex Cast Explorer and verifying service readiness...';
  Args := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{app}\configure_service.ps1') + '" -InstallDir "' +
    ExpandConstant('{app}') + '" -Port ' + GetPort('') +
    ' -EnableTMDB ' + GetTMDB('') +
    ' -CreateFirewall ' + GetFirewall('') +
    ' -AllowBetaUpdates ' + GetBeta('') +
    ' -ExpectedVersion "{#AppVersion}"' +
    ' -RemoteAdminCIDRs "' + GetRemoteCIDRs('') + '"';

  Started := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    Args, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode);
  if not Started then
    RaiseException('Unable to start the Windows service configuration. Setup is incomplete.');
  if ExitCode <> 0 then begin
    FailurePath := ExpandConstant('{commonappdata}\PlexCastExplorer\logs\installer-last-error.txt');
    FailureReason := '';
    if LoadStringFromFile(FailurePath, FailureReason) then
      FailureReason := Trim(FailureReason);
    if Length(FailureReason) > 300 then
      FailureReason := Copy(FailureReason, 1, 300) + '...';
    if FailureReason = '' then
      FailureReason := 'The Windows configuration step did not report an error message.';
    RaiseException('Service configuration failed (exit code ' +
      IntToStr(ExitCode) + '): ' + FailureReason +
      '. See C:\ProgramData\PlexCastExplorer\logs\installer-error-details.log.');
  end;
end;
