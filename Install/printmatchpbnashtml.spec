# -*- mode: python ; coding: utf-8 -*-

import os, sys
sys.path.insert(0, SPECPATH)
from build_excludes import EXCLUDES

from PyInstaller.utils.hooks import collect_dynamic_libs
import endplay._dds

# Collect the dds.dll
binaries = collect_dynamic_libs('endplay._dds')

block_cipher = None


a = Analysis(
    ['..\\src\\printmatchpbnashtml.py'],
    pathex=[],
    binaries=binaries,
    datas=[('..\\src\\viz.css', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='printmatchpbnashtml',
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
