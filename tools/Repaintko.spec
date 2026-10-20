from pathlib import Path
import os, sys
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, copy_metadata
root=Path(SPECPATH).parent
app=root/'app'
assets=Path(os.environ['REPAINTKO_ASSET_ROOT'])
paths=[str(app)]+[p for p in os.environ.get('REPAINTKO_EXTRA_PATHS','').split(os.pathsep) if p]
sys.path[:0]=paths
data=[(str(app/'assets'),'assets'),(str(app/'addons'),'addons'),(str(app/'TERMS.txt'),'.')]
for folder in ('models','text_ai_runtime','video_tools'):
    if not (assets/folder).is_dir():raise ValueError('Required runtime assets missing: '+folder)
    data.append((str(assets/folder),folder))
data.append((str(assets/'addons/wallpaper-plus.rpkaddon'),'addons'))
data.append((str(root/'dist/RepaintkoUpdater.exe'),'.'))
hidden=collect_submodules('sqlglot.dialects')+collect_submodules('pymysql')+collect_submodules('websockets')+['pyodbc','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineCore','PySide6.QtPdf','PySide6.QtSvg','cryptography','_cffi_backend','onnxruntime']
for package in ('sqlglot','PyMySQL','pyodbc','cryptography','onnxruntime','websockets'):
    data+=copy_metadata(package)
a=Analysis([str(app/'repaintko.py')],pathex=paths,binaries=collect_dynamic_libs('onnxruntime'),datas=data,hiddenimports=hidden,hookspath=[str(root/'tools/hooks')],excludes=['tkinter','matplotlib','IPython','pytest','torch','tensorflow'])
a.binaries=[entry for entry in a.binaries if entry[0].lower() not in ('icuuc.dll','icudt78.dll')]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Repaintko',console=False,upx=False,icon=str(app/'assets/repaintko-free.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Repaintko')
