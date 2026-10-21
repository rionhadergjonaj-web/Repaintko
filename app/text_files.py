"""Lossless text IO and atomic saves for ReTexto."""
from pathlib import Path
import hashlib, os, tempfile

ENCODINGS=('utf-8','utf-8-sig','utf-16-le','utf-16-be','cp1252')
def digest(data):return hashlib.sha256(data).hexdigest()
def read_text(path):
    path=Path(path)
    if path.stat().st_size>64*1024*1024:raise ValueError('Diese Datei ist größer als 64 MB.')
    data=path.read_bytes()
    if data.startswith(b'\xff\xfe'):encoding='utf-16-le';text=data[2:].decode(encoding)
    elif data.startswith(b'\xfe\xff'):encoding='utf-16-be';text=data[2:].decode(encoding)
    elif data.startswith(b'\xef\xbb\xbf'):encoding='utf-8-sig';text=data.decode(encoding)
    else:
        try:encoding='utf-8';text=data.decode(encoding)
        except UnicodeDecodeError:encoding='cp1252';text=data.decode(encoding)
    if '\0' in text:raise ValueError('Die Datei enthält Binärdaten und ist keine unterstützte Textdatei.')
    eol='\r\n' if '\r\n' in text else ('\r' if '\r' in text else '\n')
    return text.replace('\r\n','\n').replace('\r','\n'),encoding,eol,digest(data)
def write_text(path,text,encoding,eol,expected=None):
    path=Path(path)
    if expected is not None and (not path.exists() or digest(path.read_bytes())!=expected):
        raise FileExistsError('Die Datei wurde außerhalb von ReTexto geändert oder entfernt.')
    data=text.replace('\r\n','\n').replace('\r','\n').replace('\n',eol).encode(encoding)
    if encoding=='utf-16-le':data=b'\xff\xfe'+data
    elif encoding=='utf-16-be':data=b'\xfe\xff'+data
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return digest(data)
