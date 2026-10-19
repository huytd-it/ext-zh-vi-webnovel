#define AppName "Novel Local"
#define AppVersion "0.1.0"
[Setup]
AppId={{51B6C679-28D1-49F7-85C7-17B1DD49F630}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\NovelLocal
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\artifacts
OutputBaseFilename=NovelLocal-0.1.0-Windows-x64-setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\NovelLocal.exe
[Files]
Source: "..\..\dist\NovelLocal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Novel Local"; Filename: "{app}\NovelLocal.exe"
Name: "{userdesktop}\Novel Local"; Filename: "{app}\NovelLocal.exe"
[Run]
Filename: "{app}\NovelLocal.exe"; Description: "Mở Novel Local"; Flags: nowait postinstall skipifsilent
; Deliberately no startup task, GPU DLL, model weights or user-data deletion.
