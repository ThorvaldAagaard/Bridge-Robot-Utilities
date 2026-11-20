# -*- mode: python ; coding: utf-8 -*-

import os, sys
sys.path.insert(0, SPECPATH)
from build_excludes import EXCLUDES
from PyInstaller.utils.hooks import collect_dynamic_libs

# endplay loads DDS from endplay/_dds/dds.dll beside its wrapper; PyInstaller does not
# see that ctypes load, so ship the DLL there. Par is computed per board (datumscore.py).


a = Analysis(
    ['..\\src\\Split_PBN.py'],
    pathex=[],
    binaries=[('..\\bin\\dds.dll', '.')] + collect_dynamic_libs('endplay'),
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Split_PBN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
