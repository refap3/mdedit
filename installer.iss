; MDEdit — Inno Setup installer script
; Run: iscc installer.iss

#define AppName    "MDEdit"
#define AppVersion "1.0.0"
#define AppExe     "MDEdit.exe"
#define AppURL     "https://github.com/refap3/mdedit"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=MDEdit-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763   ; Windows 10 1809+

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; All PyInstaller output — recurse the entire folder
Source: "dist\MDEdit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";                       Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}";             Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";               Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Associate .md and .markdown files with MDEdit
Root: HKCR; Subkey: ".md";                         ValueType: string; ValueName: ""; ValueData: "MDEdit.Document"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".markdown";                   ValueType: string; ValueName: ""; ValueData: "MDEdit.Document"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "MDEdit.Document";             ValueType: string; ValueName: ""; ValueData: "Markdown Document"; Flags: uninsdeletekey
Root: HKCR; Subkey: "MDEdit.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKCR; Subkey: "MDEdit.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
