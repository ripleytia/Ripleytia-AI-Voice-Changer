[Setup]
AppName=Ripleytia AI Ses Degistirici
AppVersion=1.0.0 Beta
AppPublisher=Ripleytia
DefaultDirName={pf}\Ripleytia_AI_Ses_Degistirici
DefaultGroupName=Ripleytia AI Ses Degistirici
OutputDir=Output
OutputBaseFilename=Ripleytia_Voice_Changer_Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Derlenmis EXE dosyasi (build_release.py ciktisi)
Source: "dist\Ripleytia_AI_Ses_Degistirici.exe"; DestDir: "{app}"; Flags: ignoreversion
; Gerekli VCRUNTIME (Eger kullanicinin makinesinde yoksa) veya baska DLLler eklenebilir.

[Icons]
Name: "{group}\Ripleytia AI Ses Degistirici"; Filename: "{app}\Ripleytia_AI_Ses_Degistirici.exe"
Name: "{commondesktop}\Ripleytia AI Ses Degistirici"; Filename: "{app}\Ripleytia_AI_Ses_Degistirici.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Ripleytia_AI_Ses_Degistirici.exe"; Description: "{cm:LaunchProgram,Ripleytia AI Ses Degistirici}"; Flags: nowait postinstall skipifsilent
