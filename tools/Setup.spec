from pathlib import Path
root=Path(SPECPATH).parent
a=Analysis([str(root/'tools/setup_bootstrap.py')],pathex=[],binaries=[],datas=[(str(root/'outputs/Repaintko-Setup-13.1.0.msi'),'.'),(str(root/'work/setup-payload1310.json'),'.')],hiddenimports=[],hookspath=[],runtime_hooks=[],excludes=['tkinter','PySide6'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='Repaintko-Setup-13.1.0',cdict={'DATA':False,'BINARY':True,'EXTENSION':True,'PYMODULE':True,'PYSOURCE':True,'PYZ':False},debug=False,strip=False,upx=False,console=False,icon=str(root/'app/assets/repaintko-free.ico'))
