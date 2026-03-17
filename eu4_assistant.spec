# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for EU4 Assistant Bot
# Build: pyinstaller eu4_assistant.spec --clean
# Output: dist/eu4-assistant.exe (Windows standalone, no console)

block_cipher = None

a = Analysis(
    ['eu4_assistant_bot/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'eu4_assistant_bot',
        'eu4_assistant_bot.ui',
        'eu4_assistant_bot.mod',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'watchdog.observers',
        'watchdog.events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy'],
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
    name='eu4-assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
