"""User-selected browser migration. Does not decrypt browser profiles or cookies."""
import csv,json,sqlite3,os,time
from pathlib import Path
from html.parser import HTMLParser
from browser_store import atomic,clean_url,origin

def profiles(base=None):
    base=Path(base or os.environ.get('LOCALAPPDATA',''))
    found=[]
    for browser,relative in [('Chrome','Google/Chrome/User Data'),('Edge','Microsoft/Edge/User Data')]:
        root=base/relative
        if root.is_dir():
            for path in [root/'Default']+sorted(root.glob('Profile *')):
                if path.is_dir():found.append((browser+' · '+path.name,path))
    return found

def read_profile(path,bookmarks=True,history=True):
    path=Path(path);out={'bookmarks':[],'history':[],'truncated':False}
    if bookmarks and (path/'Bookmarks').is_file():
        source=path/'Bookmarks'
        if source.stat().st_size>30_000_000:raise ValueError('Lesezeichendatei zu groß.')
        def walk(item,folder=''):
            if item.get('type')=='url':
                url=clean_url(item.get('url',''))
                if url:out['bookmarks'].append(dict(url=url,title=item.get('name',url)[:500],folder=folder))
            for child in item.get('children',[]):walk(child,folder+'/'+item.get('name',''))
        for item in json.loads(source.read_text(encoding='utf-8'))['roots'].values():walk(item)
    if history and (path/'History').is_file():
        source=sqlite3.connect((path/'History').resolve().as_uri()+'?mode=ro',uri=True,timeout=3)
        try:
            rows=source.execute('SELECT url,title,last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 100001').fetchall();out['truncated']=len(rows)>100000
            for url,title,stamp in rows[:100000]:
                url=clean_url(url)
                if url:
                    try:date=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(stamp/1000000-11644473600))
                    except (ValueError,OSError,OverflowError):date=''
                    out['history'].append(dict(url=url,title=(title or url)[:500],time=date))
        finally:source.close()
    return out

def merge_profile(store,data):
    with store.lock:return _merge_profile(store,data)

def _merge_profile(store,data):
    for kind in ('bookmarks','history'):
        path=store.root/(kind+'.json');old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else [];seen={r['url'] for r in old}
        fresh=[r for r in data[kind] if r['url'] not in seen];merged=old+fresh
        if kind=='history':merged.sort(key=lambda r:r.get('time',''),reverse=True)
        atomic(path,json.dumps(merged,ensure_ascii=False).encode('utf-8'))
    return len(data['bookmarks']),len(data['history'])

def password_csv(store,path):
    path=Path(path)
    if path.stat().st_size>30_000_000:raise ValueError('CSV maximal 30 MB.')
    rows=store.credentials();known={(r['site'],r['user']) for r in rows};added=skipped=0
    with path.open(encoding='utf-8-sig',newline='') as file:
        reader=csv.DictReader(file)
        if not {'url','username','password'}<=set(reader.fieldnames or []):raise ValueError('Chrome-/Edge-Passwort-CSV mit url, username und password benötigt.')
        for r in reader:
            try:site=origin(r['url'])
            except (ValueError,TypeError):skipped+=1;continue
            key=(site,r.get('username',''))
            if not r.get('password') or key in known:skipped+=1;continue
            rows.append(dict(site=site,user=key[1],password=r['password']));known.add(key);added+=1
    if added:store.write_credentials(rows)
    return added,skipped

def bookmarks_html(store,path):
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.href=None;self.title='';self.rows=[]
        def handle_starttag(self,tag,attrs):
            if tag.lower()=='a':self.href=dict(attrs).get('href');self.title=''
        def handle_data(self,data):
            if self.href:self.title+=data
        def handle_endtag(self,tag):
            if tag.lower()=='a' and self.href:
                url=clean_url(self.href)
                if url:self.rows.append(dict(url=url,title=self.title,folder='Import'))
                self.href=None
    path=Path(path)
    if path.stat().st_size>30_000_000:raise ValueError('HTML maximal 30 MB.')
    parser=Parser();parser.feed(path.read_text(encoding='utf-8-sig'));merge_profile(store,dict(bookmarks=parser.rows,history=[]));return len(parser.rows)
