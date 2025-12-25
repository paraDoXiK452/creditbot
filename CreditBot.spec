# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

# Безопасный поиск selenium_stealth/js
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
                print(f"Found selenium_stealth/js at: {potential_path}")
                break
    else:
        import sysconfig
        site_packages = sysconfig.get_paths()["purelib"]
        potential_path = os.path.join(site_packages, 'selenium_stealth', 'js')
        if os.path.exists(potential_path):
            selenium_stealth_js = potential_path
            print(f"Found selenium_stealth/js at: {potential_path}")
except Exception as e:
    print(f"WARNING: Could not locate selenium_stealth/js: {e}")

# Собираем datas
datas = [('zoiper_assets', 'zoiper_assets')]

if selenium_stealth_js and os.path.exists(selenium_stealth_js):
    datas.append((selenium_stealth_js, 'selenium_stealth/js'))
    print("Adding selenium_stealth/js to build")
else:
    print("WARNING: selenium_stealth/js not found, skipping")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        # Selenium и автоматизация
        'selenium_stealth',
        'undetected_chromedriver',
        'cv2',
        # КРИТИЧНО: Процессоры (импортируются в try/except)
        'core.calls_processor',
        'core.bankruptcy_processor',
        'core.comments_processor',
        'core.password_reset_processor',
        'core.writeoffs_processor',
        'core.browser',
        'core.captcha',
        'core.utils',
        # Капча и OCR
        'captcha',
        'easyocr',
        'torch',
        'torchvision',
        'PIL',
        'PIL.Image',
        'PIL.ImageEnhance',
        # Математика и обработка
        'numpy',
        'scipy',
        'skimage',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Исключаем ненужные тяжелые библиотеки
        'tensorflow',
        'transformers',
        'diffusers',
        'accelerate',
        'spacy',
        'nltk',
    ],
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
    name='CreditBot' if sys.platform == 'darwin' else 'CreditBotV{VERSION}',
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
    name='CreditBot' if sys.platform == 'darwin' else 'CreditBotV{VERSION}',
)

# macOS: Создаем .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='CreditBot.app',
        icon=None,
        bundle_identifier='com.creditbot.app',
        info_plist={
            'CFBundleName': 'CreditBot',
            'CFBundleDisplayName': 'CreditBot',
            'CFBundleVersion': '{VERSION}',
            'CFBundleShortVersionString': '{VERSION}',
            'NSHighResolutionCapable': True,
        },
    )