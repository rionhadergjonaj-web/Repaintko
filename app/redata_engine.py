"""Worker-owned DB connections. SQLite, MySQL and installed Access ODBC drivers."""
import sqlite3,csv,json,os,ssl,threading
from pathlib import Path

class Database:
    def __init__(self):self.connection=None;self.kind='sqlite';self.readonly=True;self.label='Nicht verbunden';self.cancelled=threading.Event();self.active_cursor=None
    def connect(self,kind,**options):
        self.close();self.cancelled.clear();self.kind=kind;self.readonly=options.pop('readonly',True)
        if kind=='sqlite':
            path=Path(options['path']).resolve();new=options.get('create',False)
            if new and path.exists():raise ValueError('Die Datei existiert bereits. Bitte öffnen oder einen neuen Namen wählen.')
            self.connection=sqlite3.connect(path.as_uri()+('?mode=ro' if self.readonly else '?mode=rwc' if new else '?mode=rw'),uri=True,timeout=10)
            self.connection.execute('PRAGMA foreign_keys=ON');self.connection.set_progress_handler(lambda:1 if self.cancelled.is_set() else 0,1000);self.label=str(path)
        elif kind=='mysql':
            import pymysql
            self.connection=pymysql.connect(host=options['host'],port=int(options.get('port',3306)),user=options['user'],password=options['password'],database=options.get('database') or None,connect_timeout=10,read_timeout=30,write_timeout=30,charset='utf8mb4',autocommit=False,ssl=ssl.create_default_context() if options.get('tls',True) else None)
            if self.readonly:
                with self.connection.cursor() as cur:cur.execute('SET SESSION TRANSACTION READ ONLY')
            self.label=options['host']+'/'+(options.get('database') or '')
        elif kind=='access':
            import pyodbc
            drivers=[d for d in pyodbc.drivers() if 'Access' in d and '*.accdb' in d]
            if not drivers:raise RuntimeError('Microsoft Access Database Engine (64 Bit) ist nicht installiert. Bitte den Microsoft Access ODBC-Treiber installieren.')
            path=Path(options['path']).resolve()
            if not path.is_file():raise ValueError('Access-Datei nicht gefunden.')
            if ';' in str(path):raise ValueError('Der Access-Treiber benötigt einen Dateipfad ohne Semikolon.')
            self.connection=pyodbc.connect('DRIVER={'+drivers[-1]+'};DBQ='+str(path)+';',autocommit=False,readonly=self.readonly,timeout=10);self.label=str(path)
        else:raise ValueError('Unbekannter Datenbanktyp.')
        return self.tables()
    def close(self):
        if self.connection:
            try:self.connection.rollback()
            finally:self.connection.close();self.connection=None
    def require(self):
        if self.connection is None:raise ValueError('Zuerst eine Datenbank öffnen.')
    def quote(self,name):
        if not isinstance(name,str) or not name or '\x00' in name:raise ValueError('Ungültiger Name.')
        if self.kind=='mysql':return '`'+name.replace('`','``')+'`'
        if self.kind=='access':return '['+name.replace(']',']]')+']'
        return '"'+name.replace('"','""')+'"'
    def tables(self):
        self.require();cur=self.connection.cursor()
        try:
            if self.kind=='sqlite':return [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            if self.kind=='mysql':cur.execute('SHOW FULL TABLES');return [r[0] for r in cur.fetchall()]
            return sorted({r.table_name for r in cur.tables() if r.table_type in ('TABLE','VIEW') and not r.table_name.startswith('MSys')})
        finally:cur.close()
    def execute(self,script,commit=False):
        self.require();self.cancelled.clear()
        import sqlglot
        dialect='mysql' if self.kind=='mysql' else 'tsql' if self.kind=='access' else 'sqlite'
        trees=sqlglot.parse(script,read=dialect);results=[]
        if len(trees)>200:raise ValueError('Maximal 200 Anweisungen je Lauf.')
        from sqlglot import exp
        if self.readonly and any(t is not None and (not isinstance(t,exp.Query) or t.find(exp.Into) is not None) for t in trees):raise ValueError('Schreibschutz aktiv. Zum Bearbeiten zuerst neu ohne Schreibschutz verbinden.')
        cursor=self.connection.cursor()
        self.active_cursor=cursor
        try:
            if self.kind=='sqlite' and not self.readonly and not self.connection.in_transaction:self.connection.execute('BEGIN')
            for tree in trees:
                if tree is None:continue
                if self.cancelled.is_set():raise RuntimeError('Abgebrochen.')
                cursor.execute(tree.sql(dialect=dialect))
                if cursor.description:
                    rows=cursor.fetchmany(1001);results.append(dict(columns=[c[0] for c in cursor.description],rows=[list(r) for r in rows[:1000]],truncated=len(rows)>1000,count=len(rows[:1000])))
                else:results.append(dict(columns=['Betroffene Zeilen'],rows=[[cursor.rowcount]],truncated=False,count=cursor.rowcount))
            if commit:self.connection.commit()
            return results
        except Exception:self.connection.rollback();raise
        finally:self.active_cursor=None;cursor.close()
    def transaction(self,commit):
        self.require();self.connection.commit() if commit else self.connection.rollback();return 'Commit abgeschlossen' if commit else 'Rollback abgeschlossen'
    def cancel(self):
        self.cancelled.set()
        if self.kind=='sqlite' and self.connection:self.connection.interrupt()
        if self.kind=='access' and self.active_cursor:
            try:self.active_cursor.cancel()
            except Exception:pass
    def browse(self,table,offset=0):
        self.require();q=self.quote(table);cur=self.connection.cursor()
        try:
            if self.kind=='access':cur.execute('SELECT TOP 500 * FROM '+q)
            else:cur.execute('SELECT * FROM '+q+' LIMIT 500 OFFSET '+str(max(0,int(offset))))
            rows=cur.fetchall();columns=[c[0] for c in cur.description]
            return dict(columns=columns,rows=[list(r) for r in rows],table=table,offset=offset,pk=self.primary_keys(table))
        finally:cur.close()
    def primary_keys(self,table):
        cur=self.connection.cursor()
        try:
            if self.kind=='sqlite':return [r[1] for r in sorted(cur.execute('PRAGMA table_info('+self.quote(table)+')').fetchall(),key=lambda r:r[5]) if r[5]]
            if self.kind=='mysql':cur.execute('SHOW KEYS FROM '+self.quote(table)+" WHERE Key_name='PRIMARY'");return [r[4] for r in cur.fetchall()]
            metadata=access_catalog(self.label)
            for t in metadata:
                if t['name']==table:
                    return [c['name'] for key in t['keys'] if key['type']==1 for c in key['columns']]
            return []
        finally:cur.close()
    def change_row(self,table,values,original=None,delete=False):
        self.require()
        if self.readonly:raise ValueError('Schreibschutz aktiv.')
        if original is not None and not delete and not values:return 0
        placeholder='%s' if self.kind=='mysql' else '?';q=self.quote;params=[]
        if original is None:
            if not values:sql='INSERT INTO '+q(table)+(' () VALUES ()' if self.kind=='mysql' else ' DEFAULT VALUES')
            else:sql='INSERT INTO '+q(table)+' ('+', '.join(q(k) for k in values)+') VALUES ('+', '.join(placeholder for _ in values)+')';params=list(values.values())
        else:
            pk=self.primary_keys(table)
            if not pk:raise ValueError('Bearbeiten/Löschen benötigt einen Primärschlüssel. Verwende sonst den SQL-Editor.')
            # Compare all original values to avoid silently overwriting concurrent changes.
            where=[]
            for k,v in original.items():
                if v is None:where.append(q(k)+' IS NULL')
                else:where.append(q(k)+'='+placeholder);params.append(v)
            if delete:sql='DELETE FROM '+q(table)+' WHERE '+' AND '.join(where)
            else:sql='UPDATE '+q(table)+' SET '+', '.join(q(k)+'='+placeholder for k in values)+' WHERE '+' AND '.join(where);params=list(values.values())+params
        cur=self.connection.cursor()
        try:
            cur.execute(sql,params)
            if original is not None and cur.rowcount!=1:raise ValueError('Zeile wurde inzwischen geändert. Neu laden und erneut versuchen.')
            return cur.rowcount
        except Exception:self.connection.rollback();raise
        finally:cur.close()
    def schema_sql(self):
        self.require();cur=self.connection.cursor()
        try:
            if self.kind=='sqlite':return '\n\n'.join(r[0]+';' for r in cur.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END,name").fetchall())
            if self.kind=='mysql':
                out=[]
                for table in self.tables():cur.execute('SHOW CREATE TABLE '+self.quote(table));out.append(cur.fetchone()[1]+';')
                return '\n\n'.join(out)
            from sql_schema import quoted
            out=[]
            for table in access_catalog(self.label):
                fields=[quoted(r['name'])+' '+('INTEGER' if r['type'] in (2,3,11,16,17,18,19,20,21) else 'REAL' if r['type'] in (4,5,6,14,131) else 'BLOB' if r['type'] in (128,204,205) else 'TEXT') for r in table['columns']]
                for key in table['keys']:
                    columns=', '.join(quoted(c['name']) for c in key['columns'])
                    if key['type']==1:fields.append('PRIMARY KEY ('+columns+')')
                    elif key['type']==3:fields.append('UNIQUE ('+columns+')')
                    elif key['type']==2:fields.append('FOREIGN KEY ('+columns+') REFERENCES '+quoted(key['target'])+' ('+', '.join(quoted(c['target']) for c in key['columns'])+')')
                out.append('CREATE TABLE '+quoted(table['name'])+' ('+', '.join(fields)+');')
            return '\n\n'.join(out)
        finally:cur.close()
    def backup(self,path):
        if self.kind!='sqlite':raise ValueError('Datei-Backup ist für SQLite verfügbar. Andere Systeme: Schema/CSV exportieren oder Server-Backup verwenden.')
        if self.connection.in_transaction:raise ValueError('Vor dem Backup zuerst Commit oder Rollback wählen.')
        target=Path(path)
        if target.exists():raise ValueError('Backup-Ziel existiert bereits. Neuen Dateinamen wählen.')
        from contextlib import closing
        with closing(sqlite3.connect(target)) as dest:self.connection.backup(dest)
        return 'Backup gespeichert'

def create_access(path):
    import subprocess,base64
    target=Path(path).resolve()
    if target.exists():raise ValueError('Die Datei existiert bereits.')
    if target.suffix.lower()!='.accdb':raise ValueError('Für neue Access-Datenbanken .accdb verwenden.')
    encoded=base64.b64encode(str(target).encode('utf-8')).decode('ascii')
    script="$ErrorActionPreference='Stop'; $p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"')); $c=New-Object -ComObject ADOX.Catalog; $c.Create('Provider=Microsoft.ACE.OLEDB.12.0;Data Source=\"'+$p.Replace('\"','\"\"')+'\";'); [Runtime.InteropServices.Marshal]::FinalReleaseComObject($c) | Out-Null"
    exe=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,creationflags=getattr(__import__('subprocess'),'CREATE_NO_WINDOW',0),timeout=30)
    if result.returncode or not target.is_file():raise RuntimeError('Access-Datei konnte nicht erstellt werden. Microsoft Access Database Engine / ACE (64 Bit) muss installiert sein.')
    return str(target)

def access_catalog(path):
    import subprocess,base64
    encoded=base64.b64encode(str(Path(path).resolve()).encode('utf-8')).decode()
    script="""$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__PATH__'))
$catalog=New-Object -ComObject ADOX.Catalog
$catalog.ActiveConnection='Provider=Microsoft.ACE.OLEDB.12.0;Data Source="'+$p.Replace('"','""')+'";'
$tables=@()
foreach($t in $catalog.Tables){
 if($t.Type -ne 'TABLE'){continue}
 $columns=@(); foreach($c in $t.Columns){$columns+=@{name=$c.Name;type=[int]$c.Type}}
 $keys=@(); foreach($k in $t.Keys){
  $items=@();foreach($c in $k.Columns){$items+=@{name=$c.Name;target=$c.RelatedColumn}}
  $keys+=@{name=$k.Name;type=[int]$k.Type;target=$k.RelatedTable;columns=$items}
 }
 $tables+=@{name=$t.Name;columns=$columns;keys=$keys}
}
ConvertTo-Json -InputObject $tables -Depth 8 -Compress
[Runtime.InteropServices.Marshal]::FinalReleaseComObject($catalog) | Out-Null
""".replace('__PATH__',encoded)
    exe=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    if result.returncode:raise RuntimeError('Access-Schlüsselinformationen konnten nicht gelesen werden. Zuerst Änderungen committen; ACE/ADOX muss installiert sein.')
    return json.loads(result.stdout.decode('utf-8-sig'))
