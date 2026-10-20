"""Offline installation of ReDrawko's data-only template pack."""
import json
from pathlib import Path
from redraw_model import validate, atomic_write

BUNDLE=Path(__file__).parent/'addons'/'redrawko.json'

class ReDrawkoStore:
    def __init__(self,root):self.root=Path(root)/'ReDrawko';self.path=self.root/'templates.json'
    def installed(self):
        try:self.templates();return True
        except (OSError,ValueError,TypeError,KeyError):return False
    def templates(self):
        if self.path.stat().st_size>4_000_000:raise ValueError('Ungültiges Vorlagenpaket.')
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('format')!='ReDrawko Add-on' or data.get('version')!=1:raise ValueError('Unbekanntes Add-on.')
        result=data['templates']
        if set(result)!={'empty','erm','flow','uml','network','mindmap'}:raise ValueError('Unvollständige Vorlagen.')
        for document in result.values():validate(document)
        return result
    def install(self):
        raw=BUNDLE.read_bytes()
        if len(raw)>4_000_000:raise ValueError('Vorlagenpaket zu groß.')
        data=json.loads(raw)
        if data.get('format')!='ReDrawko Add-on' or data.get('version')!=1:raise ValueError('Ungültiges Add-on.')
        if set(data['templates'])!={'empty','erm','flow','uml','network','mindmap'}:raise ValueError('Unvollständiges Add-on.')
        for document in data['templates'].values():validate(document)
        self.root.mkdir(parents=True,exist_ok=True);atomic_write(self.path,raw)
    def uninstall(self):
        # Remove only this pack's known file; never touch user diagrams/recovery.
        self.path.unlink(missing_ok=True)
