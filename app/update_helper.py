"""Separate installer process; re-verifies signed metadata before execution."""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from update_core import verify_manifest
from update_trust import PUBLIC_KEY, APP_VERSION


def install(job_file):
    job_path = Path(job_file).resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    manifest = job_path.with_name("version.json")
    payload = verify_manifest(manifest.read_bytes(), bytes.fromhex(PUBLIC_KEY), APP_VERSION)
    if payload is None:
        raise ValueError("Kein neueres Update.")
    installer = job_path.with_name("setup.msi")
    digest = hashlib.sha256()
    with installer.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    if installer.stat().st_size != payload["size"] or digest.hexdigest() != payload["sha256"]:
        raise ValueError("Installationsdatei wurde verändert.")
    executable = Path(job["executable"]).resolve()
    # Never accept arbitrary executables or a shell command from the job file.
    if executable.name.lower() != "repaintko.exe" or not executable.is_file():
        raise ValueError("Ungültiger Neustartpfad.")
    pid = job["pid"]
    if type(pid) is not int or pid <= 0:
        raise ValueError("Ungültiger Prozess.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    process = kernel.OpenProcess(0x100000, False, pid)
    if process:
        try:
            if kernel.WaitForSingleObject(process, 10*60*1000) != 0:
                raise ValueError("Die App wurde nicht geschlossen; Update abgebrochen.")
        finally:
            kernel.CloseHandle(process)
    # MSI owns rollback and UAC. No manual replacement/deletion of app files.
    result = subprocess.run(["msiexec.exe", "/i", str(installer), "/passive", "/norestart",
                             "/L*v", str(job_path.with_name("install.log"))], check=False)
    job_path.with_name("result.json").write_text(json.dumps(dict(exit_code=result.returncode)), encoding="utf-8")
    if result.returncode in (0, 3010):
        subprocess.Popen([str(executable)], cwd=executable.parent)
    else:
        # Existing installation remains managed by MSI rollback.
        ctypes.windll.user32.MessageBoxW(None, "Das Update konnte nicht installiert werden. Bitte Repaintko erneut starten. Details stehen im Update-Protokoll.", "Repaintko Update", 16)
    return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(install(sys.argv[1]))
    except Exception:
        ctypes.windll.user32.MessageBoxW(None, "Updateprüfung fehlgeschlagen. Es wurde kein Installer ausgeführt.", "Repaintko Update", 16)
        sys.exit(1)
