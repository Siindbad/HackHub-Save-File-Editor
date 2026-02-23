# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import re

from PyInstaller.utils.hooks import collect_submodules

_SPEC_FILE = globals().get("__file__", "")
PROJECT_ROOT = Path(_SPEC_FILE).resolve().parent if _SPEC_FILE else Path.cwd()
ASSETS_DIR = PROJECT_ROOT / "assets"


def _build_asset_datas():
    # Runtime packaging allowlist-by-exclusion:
    # - Keep app/runtime assets, drop dev-only docs/previews/templates from dist payloads.
    excluded_exact = {
        "session-log-archive.md",
        "readme-layout-preview.html",
    }
    excluded_prefixes = (
        "readme-backups/",
        "previews/",
        "readme-template/",
    )
    datas = []
    for file_path in sorted(ASSETS_DIR.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(ASSETS_DIR).as_posix()
        if rel in excluded_exact:
            continue
        if any(rel.startswith(prefix) for prefix in excluded_prefixes):
            continue
        rel_parent = Path(rel).parent.as_posix()
        dest = "assets" if rel_parent == "." else f"assets/{rel_parent}"
        datas.append((str(file_path.relative_to(PROJECT_ROOT)), dest))
    return datas


def _read_app_version():
    constants_path = PROJECT_ROOT / "core" / "constants.py"
    text = constants_path.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("APP_VERSION not found in core/constants.py.")
    return match.group(1).strip()


def _version_tuple(version_text):
    tokens = str(version_text or "").strip().split(".")
    parts = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            parts.append(int(token))
            continue
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def _ensure_windows_version_file():
    app_version = _read_app_version()
    version_tuple = _version_tuple(app_version)
    build_dir = PROJECT_ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    version_path = build_dir / "windows-version-info.txt"
    version_text = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [
        StringStruct('CompanyName', 'Siindbad'),
        StringStruct('FileDescription', 'SINS Save Editor'),
        StringStruct('FileVersion', '{app_version}'),
        StringStruct('InternalName', 'sins_editor'),
        StringStruct('OriginalFilename', 'sins_editor.exe'),
        StringStruct('ProductName', 'SINS Save Editor'),
        StringStruct('ProductVersion', '{app_version}')
        ])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    version_path.write_text(version_text, encoding="utf-8")
    return str(version_path)


WINDOWS_VERSION_FILE = _ensure_windows_version_file()


a = Analysis(
    ['sins_editor.py'],
    pathex=[],
    binaries=[],
    datas=_build_asset_datas(),
    hiddenimports=collect_submodules('PIL'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

onefile_exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='sins_editor',
    icon='assets/S_icon.ico',
    version=WINDOWS_VERSION_FILE,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # Keep release binaries unpacked to reduce AV false-positive risk.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    manifest='assets/windows-longpath.manifest',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

onedir_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sins_editor',
    icon='assets/S_icon.ico',
    version=WINDOWS_VERSION_FILE,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    manifest='assets/windows-longpath.manifest',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

onedir_coll = COLLECT(
    onedir_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='sins_editor-onedir',
)
