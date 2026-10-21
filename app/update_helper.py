"""Separate installer process; re-verifies signed metadata before execution."""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from update_core import verify_manifest
from update_trust import PUBLIC_KEY, APP_VERSION


def verify_msi(installer, expected_version):
    api = ctypes.WinDLL('msi')
    handle = ctypes.c_uint
    db, view, record = handle(), handle(), handle()
    api.MsiOpenDatabaseW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(handle)]
    api.MsiDatabaseOpenViewW.argtypes = [handle, ctypes.c_wchar_p, ctypes.POINTER(handle)]
    api.MsiRecordGetStringW.argtypes = [handle, ctypes.c_uint, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint)]
    def checked(code):
        if code: raise ValueError('Installer-Metadaten konnten nicht geprüft werden.')
    checked(api.MsiOpenDatabaseW(str(installer), None, ctypes.byref(db)))
    try:
        expected_upgrade = '{'+str(uuid.uuid5(uuid.NAMESPACE_URL,'repainko.app/upgrade')).upper()+'}'
        for prop, expected in [('ProductVersion',expected_version),('ProductName','Repaintko'),('UpgradeCode',expected_upgrade)]:
            checked(api.MsiDatabaseOpenViewW(db, f"SELECT `Value` FROM `Property` WHERE `Property`='{prop}'", ctypes.byref(view)))
            try:
                checked(api.MsiViewExecute(view,0));checked(api.MsiViewFetch(view,ctypes.byref(record)))
                buffer=ctypes.create_unicode_buffer(256);length=ctypes.c_uint(256)
                checked(api.MsiRecordGetStringW(record,1,buffer,ctypes.byref(length)))
                if buffer.value != expected: raise ValueError('Installer passt nicht zur signierten Veröffentlichung.')
            finally:
                if record.value:api.MsiCloseHandle(record);record=handle()
                if view.value:api.MsiCloseHandle(view);view=handle()
    finally:
        api.MsiCloseHandle(db)


def verify_job(job_file, current=APP_VERSION):
    job_path = Path(job_file).resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    manifest = job_path.with_name("version.json")
    payload = verify_manifest(manifest.read_bytes(), bytes.fromhex(PUBLIC_KEY), current)
    if payload is None:
        raise ValueError("Kein neueres Update.")
    installer = job_path.with_name("setup.msi")
    digest = hashlib.sha256()
    with installer.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    if installer.stat().st_size != payload["size"] or digest.hexdigest() != payload["sha256"]:
        raise ValueError("Installationsdatei wurde verändert.")
    verify_msi(installer, payload['version'])
    executable = Path(job["executable"]).resolve()
    # Never accept arbitrary executables or a shell command from the job file.
    if executable.name.lower() != "repaintko.exe" or not executable.is_file():
        raise ValueError("Ungültiger Neustartpfad.")
    pid = job["pid"]
    if type(pid) is not int or pid <= 0:
        raise ValueError("Ungültiger Prozess.")
    return job_path, job, installer, executable


def install(job_file):
    job_path, job, installer, executable = verify_job(job_file)
    pid = job["pid"]
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
        if len(sys.argv) == 4 and sys.argv[1] == '--verify-only':
            verify_job(sys.argv[2], current='0.0.0')
            Path(sys.argv[3]).write_text(json.dumps(dict(ok=True)),encoding='utf-8')
            sys.exit(0)
        sys.exit(install(sys.argv[1]))
    except Exception:
        if len(sys.argv) == 4 and sys.argv[1] == '--verify-only':
            Path(sys.argv[3]).write_text(json.dumps(dict(ok=False)),encoding='utf-8')
            sys.exit(1)
        ctypes.windll.user32.MessageBoxW(None, "Updateprüfung fehlgeschlagen. Es wurde kein Installer ausgeführt.", "Repaintko Update", 16)
        sys.exit(1)
