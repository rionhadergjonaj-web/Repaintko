"""Optional data-only installation marker for the packaged ReDataKo engine."""
import json
from pathlib import Path
from redraw_model import atomic_write

class ReDataStore:
    def __init__(self,root):self.root=Path(root)/'ReDataKo';self.path=self.root/'plugin.json'
    def installed(self):
        try:return json.loads(self.path.read_text(encoding='utf-8'))=={'plugin':'ReDataKo','version':1}
        except (OSError,ValueError):return False
    def install(self):self.root.mkdir(parents=True,exist_ok=True);atomic_write(self.path,b'{"plugin":"ReDataKo","version":1}')
    def uninstall(self):self.path.unlink(missing_ok=True)
