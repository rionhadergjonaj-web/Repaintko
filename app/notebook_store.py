"""Transactional local notebook with a strict 100-note limit."""
import sqlite3,uuid,time
from pathlib import Path
class NoteStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=2)
        self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, updated REAL NOT NULL, revision INTEGER NOT NULL DEFAULT 0)')
        self.db.execute("CREATE TRIGGER IF NOT EXISTS note_limit BEFORE INSERT ON notes WHEN (SELECT COUNT(*) FROM notes)>=100 BEGIN SELECT RAISE(ABORT,'Maximal 100 Notizen'); END")
        self.db.commit()
    def list(self,query=''):
        rows=self.db.execute('SELECT id,title,body,updated,revision FROM notes ORDER BY updated DESC,id').fetchall();q=query.casefold()
        return [dict(r) for r in rows if q in (r['title']+' '+r['body']).casefold()]
    def count(self):return self.db.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
    def get(self,key):
        row=self.db.execute('SELECT * FROM notes WHERE id=?',(key,)).fetchone()
        if row is None:raise ValueError('Die Notiz wurde in einem anderen Fenster gelöscht.')
        return dict(row)
    def create(self):
        key=uuid.uuid4().hex
        try:
            with self.db:self.db.execute('INSERT INTO notes VALUES (?,?,?,?,0)',(key,'Neue Notiz','',time.time()))
        except sqlite3.IntegrityError as exc:raise ValueError('Maximal 100 Notizen. Lösche zuerst eine bestehende Notiz.') from exc
        return self.get(key)
    def save(self,key,title,body,revision):
        title=title.strip() or 'Ohne Titel'
        if len(title)>200:raise ValueError('Der Titel darf höchstens 200 Zeichen enthalten.')
        with self.db:
            result=self.db.execute('UPDATE notes SET title=?,body=?,updated=?,revision=revision+1 WHERE id=? AND revision=?',(title,body,time.time(),key,revision))
            if result.rowcount!=1:raise ValueError('Diese Notiz wurde in einem anderen Repaintko-Fenster geändert. Kopiere deinen Text zur Sicherheit und lade die Notiz neu.')
        return self.get(key)
    def delete(self,key,revision):
        with self.db:
            result=self.db.execute('DELETE FROM notes WHERE id=? AND revision=?',(key,revision))
            if result.rowcount!=1:raise ValueError('Die Notiz wurde zwischenzeitlich geändert. Bitte neu laden.')
    def close(self):self.db.close()
