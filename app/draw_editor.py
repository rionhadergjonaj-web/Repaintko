"""The ordinary Paint window embedded in a live DrawTogether session."""
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication,QMessageBox,QFileDialog
from qt_app import Repainko
from draw_edits import clone,prepare,compress,inverse,identify

def history_bytes(value):
    if isinstance(value,str):return len(value)
    if isinstance(value,dict):return sum(history_bytes(v) for v in value.values())
    if isinstance(value,list):return sum(history_bytes(v) for v in value)
    return 16

class SharedPaintEditor(Repainko):
    def __init__(self,owner):
        super().__init__(shared_editor=True)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.shared_bridge=PaintBridge(self,owner)
        QApplication.instance().aboutToQuit.connect(self.shared_bridge.shutdown)
        self.undo_action.triggered.disconnect();self.redo_action.triggered.disconnect()
        self.undo_action.triggered.connect(lambda:self.shared_bridge.history(False))
        self.redo_action.triggered.connect(lambda:self.shared_bridge.history(True))
    def closeEvent(self,event):event.ignore()

class PaintBridge:
    def __init__(self,editor,owner):
        self.editor=editor;self.owner=owner;self.baseline=None;self.dirty=False;self.full=False;self.boxes={};self.receiving=False
        self.executor=ThreadPoolExecutor(max_workers=1);self.future=None;self.latest=None;self.conflict=False;self.undo=[];self.redo=[];self.group=[];self.history_pending=None;self.seen_revision=-1
        self.timer=QTimer(editor);self.timer.setInterval(33);self.timer.timeout.connect(self.tick);self.timer.start()
    def reset(self):
        if self.future:self.future.cancel();self.future=None
        self.baseline=None;self.latest=None;self.dirty=False;self.full=False;self.boxes={};self.conflict=False;self.undo=[];self.redo=[];self.group=[];self.history_pending=None;self.seen_revision=-1
    def changed(self,box=None):
        if self.receiving or self.baseline is None or self.conflict:return
        if box is None:
            # Refresh after a brush release already has precise dirty rectangles.
            self.full=True
        else:
            key=self.editor.doc.layers[self.editor.doc.active].get('_shared_id')
            previous=self.boxes.get(key,box);self.boxes[key]=(min(previous[0],box[0]),min(previous[1],box[1]),max(previous[2],box[2]),max(previous[3],box[3]))
        self.dirty=True
    def frame(self,doc,revision):
        self.latest=revision
        self.tick()
    def preview(self,op):
        # Merge disjoint remote brush patches even while the local pen is down.
        # Global edits wait for the authoritative idle synchronization.
        if self.conflict or self.baseline is None or op.get('kind')!='edit' or 'replacement' in op or op.get('paper'):return
        if not (self.dirty or self.future or self.editor.canvas.start is not None):return
        if QApplication.activeModalWidget() is not None:return
        if any(c['fields'] or c.get('guard') or any(p['box'] is None for p in c['pixels']) for c in op['changes']):return
        from types import SimpleNamespace
        from draw_edits import apply_edit
        from PySide6.QtGui import QPainter
        from PIL.ImageQt import ImageQt
        def state(doc):return SimpleNamespace(doc=doc,size=doc.image.size,ids=[e.get('_shared_id') for e in doc.layers])
        try:
            live,base=state(self.editor.doc),state(self.baseline)
            apply_edit(live,op,True);apply_edit(base,op,True)
            apply_edit(live,op);apply_edit(base,op)
        except (ValueError,KeyError,TypeError):return
        painter=QPainter(self.editor.canvas.surface);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        for c in op['changes']:
            for p in c['pixels']:
                if p['field']=='image':
                    box=p['box'];painter.drawImage(box[0],box[1],ImageQt(self.editor.doc.composite(tuple(box),preserve_alpha=True)))
        painter.end();self.editor.canvas.update()
    def receive(self,doc):
        editor=self.editor;active=editor.doc.layers[editor.doc.active].get('_shared_id');selection=editor.doc.selection
        ids=[e['_shared_id'] for e in doc.layers];doc.active=ids.index(active) if active in ids else len(ids)-1
        if editor.doc.image.size==doc.image.size:doc.selection=selection
        first=self.baseline is None
        self.receiving=True
        try:
            editor.doc=doc;self.baseline=clone(doc);editor.refresh()
            if first:editor.fit()
        finally:self.receiving=False
    def fail(self,message):
        self.conflict=True;self.editor.setEnabled(True)
        self.owner.notice.setText(message+' Dein lokaler Entwurf wird nicht verworfen. Speichere ihn bei Bedarf und wähle „Neu synchronisieren“.')
        self.owner.resync_button.setVisible(True)
        # Freeze edits until the user explicitly keeps/saves the local draft.
        self.editor.canvas.setEnabled(False)
    def resync(self):
        if QMessageBox.question(self.owner,'Neu synchronisieren','Den aktuellen lokalen Entwurf durch den bestätigten gemeinsamen Stand ersetzen? Speichere ihn vorher, wenn du ihn behalten möchtest.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Yes:return
        if self.future and not self.future.done():return
        client=self.owner.client
        if not client:return
        with client.lock:
            if client.pending:return
            doc=client.document_copy();client.last_rejection=None
        self.reset();self.receive(doc);self.editor.canvas.setEnabled(True);self.owner.resync_button.hide();self.owner.notice.clear()
    def tick(self):
        import time
        point=self.editor.canvas.hover
        if point and self.owner.client and self.owner.online and time.monotonic()-getattr(self,"cursor_time",0)>.08:
            self.cursor_time=time.monotonic();self.owner.client.cursor(*point)
        client=self.owner.client
        if not client:return
        if client.last_rejection and not self.conflict:self.fail(client.last_rejection)
        if self.future and self.future.done():
            future=self.future;self.future=None
            try:
                op=future.result()
                if not self.conflict:client.submit(op);self.group.append(op);self.redo.clear()
            except Exception as exc:self.fail(str(exc))
        if self.conflict:return
        if self.owner.online and self.dirty and self.baseline is not None and self.future is None:
            try:
                op,self.baseline=prepare(self.baseline,self.editor.doc,None if self.full else self.boxes)
                self.dirty=False;self.full=False;self.boxes={}
                if op:self.future=self.executor.submit(compress,op)
            except Exception as exc:self.fail(str(exc));return
        with client.lock:pending=bool(client.pending)
        drawing=self.editor.canvas.start is not None
        modal=QApplication.activeModalWidget() is not None
        if not drawing and not modal and not self.dirty and self.future is None and not pending:
            if self.group:
                self.undo.append(self.group);self.group=[];self.undo=self.undo[-60:]
                while len(self.undo)>1 and history_bytes(self.undo)>480_000_000:self.undo.pop(0)
            if self.history_pending:
                redo,group=self.history_pending
                (self.redo if redo else self.undo).pop();(self.undo if redo else self.redo).append(group);self.history_pending=None
            if self.latest is not None:
                with client.lock:
                    if client.state is not None and not client.pending:
                        revision=client.state.revision
                        if revision!=self.seen_revision:
                            doc=client.document_copy();self.seen_revision=revision;self.receive(doc)
                self.latest=None
        self.editor.undo_action.setEnabled(bool(self.undo) and not pending and self.future is None and not drawing)
        self.editor.redo_action.setEnabled(bool(self.redo) and not pending and self.future is None and not drawing)
    def history(self,redo):
        source=self.redo if redo else self.undo
        if not source or self.future or self.dirty or self.conflict:return
        client=self.owner.client
        with client.lock:
            if client.pending:return
        group=source[-1]
        try:
            client.submit(dict(kind='batch',ops=group if redo else [inverse(op) for op in reversed(group)]));self.history_pending=(redo,group)
        except Exception as exc:self.fail(str(exc))
    def shutdown(self):
        self.timer.stop();self.executor.shutdown(wait=False,cancel_futures=True)
