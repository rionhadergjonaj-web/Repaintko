"""Exercise MSI conditions/costing and preview its own dialogs; never install files."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import json
from PIL import Image
root=Path(__file__).resolve().parents[1]
msi=c.WinDLL('msi');user=c.WinDLL('user32');gdi=c.WinDLL('gdi32')
def bind(dll,name,args,restype=w.UINT):
    f=getattr(dll,name);f.argtypes=args;f.restype=restype;return f
def check(code):
    if code:raise RuntimeError(code)
close=bind(msi,'MsiCloseHandle',[w.UINT])
internal=bind(msi,'MsiSetInternalUI',[w.UINT,c.c_void_p]);internal(2,None)
openpkg=bind(msi,'MsiOpenPackageExW',[w.LPCWSTR,w.DWORD,c.POINTER(w.UINT)])
setprop=bind(msi,'MsiSetPropertyW',[w.UINT,w.LPCWSTR,w.LPCWSTR])
evaluate=bind(msi,'MsiEvaluateConditionW',[w.UINT,w.LPCWSTR],c.c_int)
action=bind(msi,'MsiDoActionW',[w.UINT,w.LPCWSTR])
getpath=bind(msi,'MsiGetTargetPathW',[w.UINT,w.LPCWSTR,w.LPWSTR,c.POINTER(w.DWORD)])
setpath=bind(msi,'MsiSetTargetPathW',[w.UINT,w.LPCWSTR,w.LPCWSTR])
package=w.UINT();check(openpkg(str(root/'outputs/Repaintko-Setup-13.1.0.msi'),1,c.byref(package)))
check(action(package,'AppSearch'))
scenarios=[('fresh','','',True,False,False),('repair','1','',False,True,False),('upgrade','','{OLD}',False,False,True)]
for name,installed,old,*expected in scenarios:
    check(setprop(package,'Installed',installed));check(setprop(package,'OLDPRODUCTS',old))
    actual=[evaluate(package,condition)==1 for condition in ('NOT Installed AND NOT OLDPRODUCTS','Installed AND NOT REMOVE','NOT Installed AND OLDPRODUCTS')]
    assert actual==expected,(name,actual)
check(setprop(package,'Installed',''));check(setprop(package,'OLDPRODUCTS',''))
assert evaluate(package,'NOT Installed AND NOT OLDPRODUCTS AND ACCEPTTERMS <> "1"')==1
check(setprop(package,'ACCEPTTERMS','1'))
assert evaluate(package,'NOT Installed AND NOT OLDPRODUCTS AND ACCEPTTERMS <> "1"')==0
for name in ('CostInitialize','FileCost','CostFinalize'):check(action(package,name))
target=str(root/'work/custom-install-target')+'\\';check(setpath(package,'INSTALLDIR',target))
buf=c.create_unicode_buffer(4096);length=w.DWORD(4096)
check(getpath(package,'INSTALLDIR',buf,c.byref(length)));assert Path(buf.value)==Path(target)
length=w.DWORD(4096)
check(getpath(package,'D'+__import__('hashlib').sha1('_internal'.encode()).hexdigest()[:20],buf,c.byref(length)))
assert Path(buf.value)==Path(target)/'_internal',buf.value
close(package)
print('MSI scenarios, mandatory terms, custom directory and runtime subdirectory: OK')
