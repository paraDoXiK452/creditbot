# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Определяем путь к selenium_stealth/js кроссплатформенно
if sys.platform == 'win32':
    import site
    site_packages = site.getsitepackages()[0]
else:
    import sysconfig
    site_packages = sysconfig.get_paths()["purelib"]

selenium_stealth_js = os.path.join(site_packages, 'selenium_stealth', 'js')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('zoiper_assets', 'zoiper_assets'),
        (selenium_stealth_js, 'selenium_stealth/js'),
    ],
    hiddenimports=[
        'selenium_stealth',
        'undetected_chromedriver',
        'cv2',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CreditBotV{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CreditBotV{VERSION}',
)