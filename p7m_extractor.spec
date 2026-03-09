# -*- mode: python ; coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
#  p7m_extractor.spec  —  PyInstaller spec per Estrattore P7M
#  Esegui con:  pyinstaller p7m_extractor.spec
# ─────────────────────────────────────────────────────────────

block_cipher = None

a = Analysis(
    ['p7m_extractor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'asn1crypto',
        'asn1crypto.cms',
        'asn1crypto.core',
        'asn1crypto.algos',
        'asn1crypto.x509',
        'asn1crypto.pem',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EstrattoreP7M',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # nessuna finestra console nera
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='p7m_extractor.ico',  # <- decommentare se hai un'icona .ico
)
