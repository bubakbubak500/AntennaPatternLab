#define MyAppName "Antenna Pattern Lab"
#ifndef MyAppVersion
#define MyAppVersion "0.37.0"
#endif
#define MyAppPublisher "OK7PS"
#define MyAppExeName "AntennaPatternLab.exe"

[Setup]
AppId={{B7DDF2C6-503F-4A6D-A8DA-B1E28EE54163}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
DisableDirPage=auto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=AntennaPatternLab-{#MyAppVersion}-setup-win-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dynamic
SetupIconFile=..\src\antenna_pattern_lab\assets\app-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}.0
VersionInfoProductName={#MyAppName}
VersionInfoDescription={#MyAppName} Windows installer
#ifdef EnableSigning
SignTool=aplsign
SignedUninstaller=yes
#endif
; User data lives in QStandardPaths AppDataLocation and is deliberately not removed on uninstall.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
english.DependencyTitle=External tools
english.DependencyDescription=Missing tools can be downloaded by the first-run assistant only after explicit confirmation and SHA-256 verification
english.DependencyResults=Detected external tools:
english.DependencyFound=Found
english.DependencyMissing=Not found. The first-run assistant can download and launch a verified official installer after two separate confirmations.
english.HamlibLabel=Hamlib rigctld
english.WsjtxLabel=WSJT-X
english.OpenHamlib=Open the official Hamlib release page
english.OpenWsjtx=Open the official WSJT-X download page
english.UpgradeDetected=Existing version %1 was detected. Setup will update it in place to %2 and preserve application data and settings.
czech.DependencyTitle=Externí nástroje
czech.DependencyDescription=Chybějící nástroje může průvodce prvním spuštěním stáhnout jen po výslovném potvrzení a ověření SHA-256
czech.DependencyResults=Zjištěné externí nástroje:
czech.DependencyFound=Nalezeno
czech.DependencyMissing=Nenalezeno. Průvodce může stáhnout a spustit ověřený oficiální instalátor po dvou oddělených potvrzeních.
czech.HamlibLabel=Hamlib rigctld
czech.WsjtxLabel=WSJT-X
czech.OpenHamlib=Otevřít oficiální stránku vydání Hamlib
czech.OpenWsjtx=Otevřít oficiální stránku stažení WSJT-X
czech.UpgradeDetected=Byla zjištěna stávající verze %1. Instalátor ji aktualizuje na %2 ve stejné složce a zachová data i nastavení aplikace.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AntennaPatternLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\src\antenna_pattern_lab\assets\app-icon.ico"; DestDir: "{app}"; DestName: "AntennaPatternLab.ico"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AntennaPatternLab.ico"; AppUserModelID: "OK7PS.AntennaPatternLab"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AntennaPatternLab.ico"; AppUserModelID: "OK7PS.AntennaPatternLab"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DependencyPage: TOutputMsgMemoWizardPage;
  HamlibIsMissing: Boolean;
  WsjtxIsMissing: Boolean;
  ExistingVersion: String;

function ExecutableInPath(const Name: String): Boolean;
begin
  Result := FileSearch(Name, GetEnv('PATH')) <> '';
end;

function VersionedHamlibInstalled(const BaseDir: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if FindFirst(AddBackslash(BaseDir) + 'hamlib-w64-*', FindRec) then
  begin
    try
      repeat
        if ((FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
          FileExists(AddBackslash(BaseDir) + FindRec.Name + '\bin\rigctld.exe') then
        begin
          Result := True;
          Exit;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function HamlibInstalled: Boolean;
begin
  Result := ExecutableInPath('rigctld.exe') or
    FileExists(ExpandConstant('{pf}\Hamlib\bin\rigctld.exe')) or
    VersionedHamlibInstalled(ExpandConstant('{pf}')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Hamlib\bin\rigctld.exe'));
end;

function WsjtxInstalled: Boolean;
begin
  Result := ExecutableInPath('wsjtx.exe') or
    FileExists(ExpandConstant('{pf}\wsjtx\bin\wsjtx.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\wsjtx\bin\wsjtx.exe')) or
    FileExists(ExpandConstant('{sd}\WSJT\wsjtx\bin\wsjtx.exe'));
end;

function DetectionText(const Missing: Boolean): String;
begin
  if Missing then
    Result := CustomMessage('DependencyMissing')
  else
    Result := CustomMessage('DependencyFound');
end;

function ExistingInstallationVersion(var Version: String): Boolean;
var
  Key: String;
begin
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B7DDF2C6-503F-4A6D-A8DA-B1E28EE54163}_is1';
  Result :=
    RegQueryStringValue(HKCU, Key, 'DisplayVersion', Version) or
    RegQueryStringValue(HKLM, Key, 'DisplayVersion', Version);
end;

procedure InitializeWizard;
var
  Summary: String;
begin
  HamlibIsMissing := not HamlibInstalled;
  WsjtxIsMissing := not WsjtxInstalled;
  Summary :=
    CustomMessage('HamlibLabel') + ': ' + DetectionText(HamlibIsMissing) + #13#10 +
    CustomMessage('WsjtxLabel') + ': ' + DetectionText(WsjtxIsMissing);
  if ExistingInstallationVersion(ExistingVersion) then
    Summary :=
      FmtMessage(CustomMessage('UpgradeDetected'), [ExistingVersion, '{#MyAppVersion}']) +
      Chr(13) + Chr(10) + Chr(13) + Chr(10) + Summary;
  DependencyPage := CreateOutputMsgMemoPage(
    wpSelectDir,
    CustomMessage('DependencyTitle'),
    CustomMessage('DependencyDescription'),
    CustomMessage('DependencyResults'),
    Summary);
end;

function HamlibMissing: Boolean;
begin
  Result := HamlibIsMissing;
end;

function WsjtxMissing: Boolean;
begin
  Result := WsjtxIsMissing;
end;
