#ifndef AppVersion
  #error AppVersion deve ser informado pelo script de compilação.
#endif
#ifndef BundleDir
  #define BundleDir "..\dist\Entrela"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\dist\release"
#endif

[Setup]
AppId={{6EDE6034-4734-4A60-A7E5-C243E609E090}
AppName=Entrela
AppVersion={#AppVersion}
AppPublisher=Entrela
AppPublisherURL=https://github.com/ShardGem/Entrela
DefaultDirName={localappdata}\Programs\Entrela
DefaultGroupName=Entrela
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19044
OutputDir={#ReleaseDir}
OutputBaseFilename=Entrela-{#AppVersion}-windows-x64-setup
SetupIconFile=..\gui\assets\icons\entrela.ico
UninstallDisplayIcon={app}\Entrela.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Entrela"; Filename: "{app}\Entrela.exe"
Name: "{autodesktop}\Entrela"; Filename: "{app}\Entrela.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Entrela.exe"; Description: "Abrir o Entrela"; Flags: nowait postinstall skipifsilent
