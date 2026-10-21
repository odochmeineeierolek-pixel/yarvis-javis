; Inno Setup (kostenlos) – erzeugt YAVIS-Setup.exe
[Setup]
AppName=YAVIS
AppVersion=0.1.0
DefaultDirName={autopf}\YAVIS
DefaultGroupName=YAVIS
OutputDir=..\dist
OutputBaseFilename=YAVIS-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "..\dist\YAVIS\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autodesktop}\YAVIS"; Filename: "{app}\YAVIS.exe"; Tasks: desktopicon
Name: "{group}\YAVIS"; Filename: "{app}\YAVIS.exe"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: checkedonce
Name: "autostart"; Description: "YAVIS mit Windows starten"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YAVIS"; ValueData: """{app}\YAVIS.exe"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\YAVIS.exe"; Description: "YAVIS jetzt starten"; Flags: nowait postinstall skipifsilent

[Code]
function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
            FileExists(ExpandConstant('{autopf}\Ollama\ollama.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var ErrorCode: Integer;
begin
  if (CurStep = ssPostInstall) and (not OllamaInstalled) then
    if MsgBox('YAVIS braucht Ollama (kostenlos) als lokales Gehirn. Download-Seite jetzt öffnen?', mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://ollama.com/download/windows', '', '', SW_SHOW, ewNoWait, ErrorCode);
end;
