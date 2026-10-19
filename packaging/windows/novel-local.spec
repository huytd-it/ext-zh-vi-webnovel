# Build from the project root: python -m PyInstaller packaging/windows/novel-local.spec
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

root = Path(SPECPATH).parents[1]

datas, binaries, hiddenimports = [], [], []
for package in ('ctranslate2', 'sentencepiece', 'tokenizers', 'opencc', 'pystray'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis([str(root / 'local_service/__main__.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=['torch', 'transformers', 'gradio', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='NovelLocal',
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='NovelLocal')
