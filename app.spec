# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


ROOT = Path(__file__).resolve().parent
datas = collect_data_files("wechat_digest_app")
datas += [
    (str(ROOT / "src" / "wechat_digest_app" / "vendor" / "wechat_digest" / "prompt-template.txt"), "wechat_digest_app/vendor/wechat_digest"),
    (str(ROOT / "src" / "wechat_digest_app" / "vendor" / "wechat_digest" / "LICENSE.upstream.txt"), "wechat_digest_app/vendor/wechat_digest"),
    (str(ROOT / "src" / "wechat_digest_app" / "vendor" / "wechat_digest" / "NOTICE.md"), "wechat_digest_app/vendor/wechat_digest"),
]

hiddenimports = [
    "wechat_digest_app",
    "wechat_digest_app.backend",
    "wechat_digest_app.gui",
    "wechat_digest_app.vendor",
    "wechat_digest_app.vendor.wechat_digest",
    "wechat_digest_app.vendor.wechat_digest.crypto",
    "wechat_digest_app.vendor.wechat_digest.crypto.keys",
]

pathex = [str(ROOT), str(ROOT / "src")]


a = Analysis(
    ["run_gui.py"],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WeChatDigestWindows",
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WeChatDigestWindows",
)
