#define AppName "SINS Save Editor"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceRoot
  #define SourceRoot "..\\dist\\sins_editor-onedir"
#endif
#define ThemeRoot "..\\assets\\installer\\themes\\CyanNight"
#define ThemeFile ThemeRoot + "\\CharcoalDarkSlate.vsf"

#ifnexist SourceRoot + "\\sins_editor.exe"
  #error "Onedir source not found. Build dist first (expected sins_editor.exe under SourceRoot)."
#endif

#ifnexist ThemeFile
  #error "Theme file not found. Expected CharcoalDarkSlate.vsf under assets/installer/themes/CyanNight."
#endif

[Setup]
AppId={{E62E4B6C-31F0-4AB2-86A2-2A14D9984C7F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
DefaultDirName={autopf}\SINS Save Editor
DefaultGroupName=SINS Save Editor
UninstallDisplayIcon={app}\sins_editor.exe
SetupIconFile=..\assets\S_icon.ico
WizardSmallImageFile=..\assets\installer\wizard\sin_wizard_small.bmp
WizardStyle=modern
WizardStyleFile={#ThemeFile}
DisableWelcomePage=yes
Compression=lzma2
SolidCompression=yes
InternalCompressLevel=max
OutputDir=..\dist
OutputBaseFilename=sins_editor-installer
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#SourceRoot}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SINS Save Editor"; Filename: "{app}\sins_editor.exe"
Name: "{autodesktop}\SINS Save Editor"; Filename: "{app}\sins_editor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\sins_editor.exe"; Description: "Launch SINS Save Editor"; Flags: nowait postinstall skipifsilent

[Code]
// No code hooks required for native Inno WizardStyleFile theming.
