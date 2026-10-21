import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import json,hashlib,subprocess,shutil
root=Path(__file__).resolve().parents[1]
api=c.WinDLL('msi')
def fn(name,args):
    f=getattr(api,name);f.argtypes=args;f.restype=w.UINT;return f
opendb=fn('MsiOpenDatabaseW',[w.LPCWSTR,c.c_void_p,c.POINTER(w.UINT)])
viewopen=fn('MsiDatabaseOpenViewW',[w.UINT,w.LPCWSTR,c.POINTER(w.UINT)])
execute=fn('MsiViewExecute',[w.UINT,w.UINT]);fetch=fn('MsiViewFetch',[w.UINT,c.POINTER(w.UINT)])
getstr=fn('MsiRecordGetStringW',[w.UINT,w.UINT,w.LPWSTR,c.POINTER(w.DWORD)])
read=fn('MsiRecordReadStream',[w.UINT,w.UINT,c.c_void_p,c.POINTER(w.DWORD)])
close=fn('MsiCloseHandle',[w.UINT])
def check(status):
    if status:raise RuntimeError(status)
db=w.UINT();check(opendb(str(root/'outputs/Repaintko-Setup-13.1.0.msi'),None,c.byref(db)))
def query(sql):
    view=w.UINT();check(viewopen(db,sql,c.byref(view)));check(execute(view,0));return view
view=query("SELECT `Data` FROM `_Streams` WHERE `Name` = 'Repainko1310.cab'")
row=w.UINT();check(fetch(view,c.byref(row)))
cab=root/'work/verified1310-embedded.cab'
with cab.open('wb') as out:
    while True:
        buf=c.create_string_buffer(65536);length=w.DWORD(65536)
        check(read(row,1,buf,c.byref(length)))
        if not length.value:break
        out.write(buf.raw[:length.value])
close(row);close(view)
flat=root/'work/verified1310-cab-files';flat.mkdir(exist_ok=True)
subprocess.run(['expand.exe',str(cab),'-F:*',str(flat)],check=True,stdout=subprocess.DEVNULL)
def text(row,col):
    buf=c.create_unicode_buffer(4096);length=w.DWORD(4096);check(getstr(row,col,buf,c.byref(length)));return buf.value
view=query('SELECT `Directory`,`Directory_Parent`,`DefaultDir` FROM `Directory`');dirs={}
while True:
    row=w.UINT();status=fetch(view,c.byref(row))
    if status==259:break
    check(status);dirs[text(row,1)]=(text(row,2),text(row,3));close(row)
close(view)
def directory(key):
    if key=='INSTALLDIR':return Path('.')
    parent,name=dirs[key];return directory(parent)/name.split('|')[-1]
view=query('SELECT `Component`,`Directory_` FROM `Component`');components={}
while True:
    row=w.UINT();status=fetch(view,c.byref(row))
    if status==259:break
    check(status);components[text(row,1)]=text(row,2);close(row)
close(view)
manifest=json.loads((root/'work/msi-manifest1310.json').read_text())
restored=root/'work/verified1310-app';restored.mkdir(exist_ok=True)
view=query('SELECT `File`,`Component_`,`FileName` FROM `File`');count=0
while True:
    row=w.UINT();status=fetch(view,c.byref(row))
    if status==259:break
    check(status);key,component,name=(text(row,i) for i in (1,2,3));close(row)
    rel=directory(components[component])/name.split('|')[-1]
    data=(flat/key).read_bytes()
    assert hashlib.sha256(data).hexdigest()==manifest[rel.as_posix()],rel
    dest=restored/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    count+=1
close(view);close(db)
assert count==len(manifest)
print('Verified embedded MSI cabinet:',count,'files, all SHA256 hashes match.')
