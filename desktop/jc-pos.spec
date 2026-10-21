# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para empacar JC-POS como aplicación de escritorio.

Se compila SIEMPRE en Windows real (ver .github/workflows/build-windows-installer.yml),
nunca en Linux/Mac, porque PyInstaller genera binarios solo para el sistema operativo
donde corre.

El proyecto Django (core/, inventory/, clients/, sales/, reports/, config/) se agrega
como archivos de datos sueltos en vez de intentar que PyInstaller los "congele": Django
importa sus propias apps dinámicamente por nombre de texto (INSTALLED_APPS), algo que el
análisis estático de PyInstaller no puede rastrear de forma confiable. Al copiarlos tal
cual y agregarlos a sys.path (ver desktop/launcher.py), Django los lee del disco como en
cualquier despliegue normal, evitando ese problema por completo.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).parent

hiddenimports = (
    collect_submodules("django")
    + collect_submodules("whitenoise")
    + [
        "waitress",
        "dj_database_url",
        "dotenv",
        "openpyxl",
        "xlrd",
    ]
)

datas = (
    collect_data_files("django")
    + [
        (str(PROJECT_ROOT / "templates"), "templates"),
        (str(PROJECT_ROOT / "staticfiles"), "staticfiles"),
        (str(PROJECT_ROOT / "core"), "core"),
        (str(PROJECT_ROOT / "inventory"), "inventory"),
        (str(PROJECT_ROOT / "clients"), "clients"),
        (str(PROJECT_ROOT / "sales"), "sales"),
        (str(PROJECT_ROOT / "reports"), "reports"),
        (str(PROJECT_ROOT / "config"), "config"),
    ]
)

a = Analysis(
    [str(PROJECT_ROOT / "desktop" / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["gunicorn", "psycopg", "psycopg2"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jc-pos",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(PROJECT_ROOT / "desktop" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="jc-pos",
)
