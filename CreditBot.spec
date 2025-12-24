# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

# ✅ ИСПРАВЛЕНО: Безопасный поиск selenium_stealth/js
selenium_stealth_js = None

try:
    if sys.platform == 'win32':
        import site
        site_packages_list = site.getsitepackages()
        # Пробуем все возможные пути
        for sp in site_packages_list:
            potential_path = os.path.join(sp, 'selenium_stealth', 'js')
            if os.path.exists(potential_path):
                selenium_stealth_js = potential_path
                print(f"✅ Found selenium_stealth/js at: {potential_path}")
                break
    else:
        import sysconfig
        site_packages = sysconfig.get_paths()["purelib"]
        potential_path = os.path.join(site_packages, 'selenium_stealth', 'js')
        if os.path.exists(potential_path):
            selenium_stealth_js = potential_path
            print(f"✅ Found selenium_stealth/js at: {potential_path}")
except Exception as e:
    print(f"⚠️ Could not locate selenium_stealth/js: {e}")

# Собираем datas
datas = [('zoiper_assets', 'zoiper_assets')]

if selenium_stealth_js and os.path.exists(selenium_stealth_js):
    datas.append((selenium_stealth_js, 'selenium_stealth/js'))
    print(f"✅ Adding selenium_stealth/js to build")
else:
    print(f"⚠️ WARNING: selenium_stealth/js not found, skipping")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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