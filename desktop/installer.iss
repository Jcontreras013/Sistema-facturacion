; Script de Inno Setup para generar el instalador de JC-POS (Windows).
; Se compila en el workflow de GitHub Actions, con Inno Setup (ISCC.exe) corriendo
; sobre la carpeta que PyInstaller generó en dist\jc-pos\.
;
; Instala para el usuario actual (no requiere permisos de administrador), ideal para
; computadoras de pulperías/mini markets donde el dueño puede no tener esos permisos.

#define MyAppName "JC-POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "JC-System"
#define MyAppExeName "jc-pos.exe"

[Setup]
AppId={{2B9F1C2E-6B2E-4E7E-9B7E-JCPOS0000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist_installer
OutputBaseFilename=JC-POS-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\jc-pos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Restablecer contraseña de administrador"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--reset-admin"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent
