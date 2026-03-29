# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py', 'processing.py'],  # <- ajout de processing.py
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('certs/cert.pem', '.'),
        ('certs/key.pem', '.'),
    ],
    hiddenimports=[
        'jinja2',
        'jinja2.ext',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'anyio',
        'anyio._backends._asyncio',
        # libs Excel — décommentez selon ce que processing.py utilise
        # 'xlrd',
        # 'openpyxl',
        # 'xlwt',
    ],
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
    name='MaieuticAnalyzer',
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
    icon=['static\\favicon.ico'],
)