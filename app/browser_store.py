"""Local browser history and a per-Windows-user DPAPI password vault."""
import ctypes,json,os,time
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

def origin(url):
    p=urlsplit(url)
    if p.scheme.lower()!='https' or not p.hostname or p.username or p.password:raise ValueError('Passwörter nur für HTTPS-Webseiten ohne Zugangsdaten in der Adresse.')
    host=p.hostname.lower();host='['+host+']' if ':' in host else host.encode('idna').decode('ascii')
    return 'https://'+host+(':'+str(p.port) if p.port and p.port!=443 else '')

def clean_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname:return ''
    host=p.hostname;host='['+host+']' if ':' in host else host
    sensitive={'password','passwd','pwd','pass','token','access_token','id_token','refresh_token','code','state'}
    query=urlencode([(k,'[entfernt]' if k.casefold() in sensitive else v) for k,v in parse_qsl(p.query,keep_blank_values=True)])
    return urlunsplit((p.scheme,host+(':'+str(p.port) if p.port else ''),p.path,query,''))

def crypt(data,decrypt=False):
    if os.name!='nt':raise RuntimeError('Der Passwortspeicher benötigt Windows.')
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    raw=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(raw,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    api=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    fn=api.CryptUnprotectData if decrypt else api.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)];fn.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(out.data,out.size)
    finally:kernel.LocalFree(out.data)

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    try:
        with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

class BrowserStore:
    def __init__(self,root):
        from threading import RLock
        self.lock=RLock();self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def history(self):
        path=self.root/'history.json'
        if not path.exists():return []
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,list):raise ValueError('Ungültige Verlaufsdatei.')
        return data
    def visit(self,url,title):
        with self.lock:return self._visit(url,title)
    def _visit(self,url,title):
        url=clean_url(url)
        if not url:return
        rows=self.history()
        if rows and rows[0]['url']==url:rows.pop(0)
        rows.insert(0,dict(url=url,title=title[:300],time=time.strftime('%Y-%m-%d %H:%M:%S')))
        atomic(self.root/'history.json',json.dumps(rows[:100000],ensure_ascii=False).encode('utf-8'))
    def clear_history(self):
        with self.lock:atomic(self.root/'history.json',b'[]')
    def credentials(self):
        path=self.root/'passwords.dpapi'
        if not path.exists():return []
        data=json.loads(crypt(path.read_bytes(),True).decode('utf-8'))
        if not isinstance(data,list):raise ValueError('Ungültiger Passwortspeicher.')
        return data
    def save(self,site,user,password):
        site=origin(site)
        if not password:raise ValueError('Bitte ein Passwort eingeben.')
        rows=self.credentials();rows=[r for r in rows if (r['site'],r['user'])!=(site,user)];rows.append(dict(site=site,user=user,password=password));self.write_credentials(rows)
    def write_credentials(self,rows):atomic(self.root/'passwords.dpapi',crypt(json.dumps(rows,ensure_ascii=False).encode('utf-8')))
    def delete(self,site,user):self.write_credentials([r for r in self.credentials() if (r['site'],r['user'])!=(site,user)])
