# CyanNight Installer Theme Assets

This folder contains style assets used by `installer/sins_editor_installer.iss`.

## Included

- `CyanNight.vsf` (VCL style file)

## DLL requirement

No plugin DLL is required.  
The installer uses native Inno Setup `WizardStyleFile` support.

## Build command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_installer.ps1
```

To force plain installer (no CyanNight):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_installer.ps1 -DisableCyanNightTheme
```
