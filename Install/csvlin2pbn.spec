# -*- mode: python ; coding: utf-8 -*-

import os, sys
sys.path.insert(0, SPECPATH)
from build_excludes import EXCLUDES

from PyInstaller.utils.hooks import collect_dynamic_libs
import endplay._dds

# csvlin2pbn imports endplay.types.deal, which eagerly loads dds.dll. Collect it.
binaries = collect_dynamic_libs('endplay._dds')


a = Analysis(
    ['..\\src\\csvlin2pbn.py'],
    pathex=[],
    binaries=binaries,
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
    name='csvlin2pbn',
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
