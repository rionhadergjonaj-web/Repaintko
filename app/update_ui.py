"""Background update check/download; installation waits for normal safe app close."""
import json
import os
import subprocess
import sys
import threading
import shutil
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer, QStandardPaths
from PySide6.QtWidgets import QPushButton, QMessageBox, QLabel
from update_core import fetch_manifest, verify_manifest, download
from update_trust import PUBLIC_KEY, APP_VERSION


class Updater(QObject):
    progress = Signal(int)
    ready = Signal(str)
    status = Signal(str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.job = None
        self.label = QLabel()
        window.statusBar().addPermanentWidget(self.label)
        self.button = QPushButton("Update installieren")
        self.button.hide()
        window.statusBar().addPermanentWidget(self.button)
        self.button.clicked.connect(self.prepare_install)
        self.progress.connect(lambda n: self.label.setText(f"Update wird geladen · {n} %"))
        self.status.connect(self.label.setText)
        self.ready.connect(self.download_ready)
        QTimer.singleShot(5000, self.start)

    def start(self):
        def work():
            try:
                raw = fetch_manifest()
                payload = verify_manifest(raw, bytes.fromhex(PUBLIC_KEY), APP_VERSION)
                if payload is None:
                    return
                root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "updates" / payload["version"]
                root.mkdir(parents=True, exist_ok=True)
                download(payload, root/"setup.msi", lambda n,total:self.progress.emit(n*100//total))
                (root/"version.json").write_bytes(raw)
                self.ready.emit(str(root))
            except Exception:
                # Offline, unpublished or invalid metadata never blocks the editor.
                self.status.emit("Updateprüfung nicht verfügbar")
        threading.Thread(target=work, daemon=True).start()

    def download_ready(self, folder):
        self.folder = Path(folder)
        self.label.setText("Geprüftes Update bereit")
        self.button.show()
        # Normal close handling asks about unsaved work and active sessions.
        # Cancelling keeps the verified update available via the button.
        QTimer.singleShot(1000, self.prepare_install)

    def prepare_install(self):
        helper = Path(__file__).resolve().parent / "RepaintkoUpdater.exe"
        if not getattr(sys, "frozen", False) or not helper.is_file():
            QMessageBox.information(self.window, "Update", "Die automatische Installation ist im installierten Release verfügbar. Dieser Entwicklungsstand enthält noch keinen gebauten Update-Prozess.")
            return
        self.job = self.folder/"job.json"
        self.job.write_text(json.dumps(dict(pid=os.getpid(), executable=sys.executable)), encoding="utf-8")
        detached_helper = self.folder/"RepaintkoUpdater.exe"
        shutil.copy2(helper, detached_helper)
        # All existing document/session save prompts run before the helper starts.
        if self.window.close():
            subprocess.Popen([str(detached_helper), str(self.job)], creationflags=subprocess.CREATE_NO_WINDOW)
