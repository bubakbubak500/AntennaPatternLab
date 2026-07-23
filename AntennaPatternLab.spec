from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("matplotlib")
datas += [
    (
        "src/antenna_pattern_lab/assets/ne_110m_land.shp",
        "antenna_pattern_lab/assets",
    ),
    (
        "src/antenna_pattern_lab/assets/README.md",
        "antenna_pattern_lab/assets",
    ),
    (
        "src/antenna_pattern_lab/assets/app-icon.png",
        "antenna_pattern_lab/assets",
    ),
    (
        "src/antenna_pattern_lab/assets/app-icon.ico",
        "antenna_pattern_lab/assets",
    ),
]

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=["paho.mqtt.client"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AntennaPatternLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="src/antenna_pattern_lab/assets/app-icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="AntennaPatternLab",
)
