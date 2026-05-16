# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

datas = [('src/QRandLab/assets/aboutus.png', 'assets/images'), ('src/QRandLab/assets/logo.png', 'assets/images'), ('src/QRandLab/third_party/bin/QRNG.dll', 'third_party/bin'), ('src/QRandLab/third_party/bin/TZ.exe', 'third_party/bin'), ('src/QRandLab/third_party/bin/ent.exe', 'third_party/bin'), ('src/QRandLab/third_party/bin/dieharder.exe', 'third_party/bin'), ('src/QRandLab/html_templates', 'html_templates')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('tkinterweb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['src\\main.py'],
    pathex=[os.path.abspath('src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='QRandLab',
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
    icon=['src\\QRandLab\\assets\\icon2.png'],
)
