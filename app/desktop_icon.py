"""Update only this installation's desktop shortcut icon, preserving its target."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT = r"""
$ErrorActionPreference = 'Stop'
function Update-RepaintkoIcon($config) {
    $root = [IO.Path]::GetFullPath($config.app)
    $icon = Join-Path $root ('assets\repaintko-' + $config.edition + '.ico')
    if (-not (Test-Path -LiteralPath $icon -PathType Leaf)) { throw 'Die Symboldatei fehlt. Bitte Repaintko reparieren.' }
    $folders = @($config.folders)
    if ($folders.Count -eq 0) {
        $folders = @([Environment]::GetFolderPath('DesktopDirectory'), [Environment]::GetFolderPath('CommonDesktopDirectory'))
    }
    $shell = New-Object -ComObject WScript.Shell
    $targets = @((Join-Path $root 'runtime\pythonw.exe'), (Join-Path $root 'runtime\python.exe'))
    if ($config.executable) { $targets += $config.executable }
    $entries = @((Join-Path $root 'repaintko.py'), (Join-Path $root 'repainko.py'))
    $found = 0; $changed = 0; $denied = $false
    foreach ($folder in ($folders | Select-Object -Unique)) {
        if (-not $folder) { continue }
        foreach ($name in @('Repaintko.lnk','Repainko.lnk')) {
            $path = Join-Path $folder $name
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
            $link = $shell.CreateShortcut($path)
            if ($link.TargetPath -notin $targets) { continue }
            $matchesEntry = ($config.executable -and $link.TargetPath -eq $config.executable)
            foreach ($entry in $entries) {
                if ($link.Arguments.IndexOf(('"' + $entry + '"'), [StringComparison]::OrdinalIgnoreCase) -ge 0) { $matchesEntry = $true }
            }
            if (-not $matchesEntry) { continue }
            $found++
            if ($link.IconLocation -ieq ($icon + ',0') -or $link.IconLocation -ieq ($icon + ', 0')) { continue }
            try {
                $link.IconLocation = $icon + ',0'
                $link.Save()
                $changed++
            } catch { $denied = $true }
        }
    }
    if ($changed -gt 0) {
        # Notify Explorer; do not kill/restart it or clear unrelated icon caches.
        Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class RepaintkoShell { [DllImport("shell32.dll")] public static extern void SHChangeNotify(uint e, uint f, IntPtr a, IntPtr b); }' -ErrorAction SilentlyContinue
        [RepaintkoShell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    }
    if ($denied) { return 'denied' }
    if ($found -eq 0) { return 'missing' }
    if ($changed -gt 0) { return 'updated' }
    return 'current'
}
try {
    $status = Update-RepaintkoIcon $config
    if ($status -eq 'denied' -and $config.elevate) {
        $config.elevate = $false
        $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($config | ConvertTo-Json -Compress -Depth 5)))
        $functionBody = ${function:Update-RepaintkoIcon}.ToString()
        $child = '$config = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(''' + $payload + ''')) | ConvertFrom-Json; function Update-RepaintkoIcon {' + $functionBody + '}; try { $result = Update-RepaintkoIcon $config; if ($result -eq ''denied'') { exit 1 }; exit 0 } catch { exit 1 }'
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
        try {
            $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList @('-NoProfile','-NonInteractive','-EncodedCommand',$encoded) -Verb RunAs -WindowStyle Hidden -Wait -PassThru
            if ($process.ExitCode -eq 0) { $status = Update-RepaintkoIcon $config } else { $status = 'denied' }
        } catch { $status = 'cancelled' }
    }
    @{status=$status} | ConvertTo-Json -Compress
} catch {
    @{status='error';message=$_.Exception.Message} | ConvertTo-Json -Compress
}
"""


def encoded_script(app_dir, plus, allow_elevation=False, folders=None):
    config=dict(app=str(Path(app_dir).resolve()),edition='plus' if plus else 'free',elevate=allow_elevation,folders=folders or [])
    config['executable']=sys.executable if getattr(sys,'frozen',False) else ''
    payload=base64.b64encode(json.dumps(config).encode('utf-8')).decode('ascii')
    script="$config = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+payload+"')) | ConvertFrom-Json\n"+SCRIPT
    return base64.b64encode(script.encode('utf-16le')).decode('ascii')


def packaged_runtime(app_dir):
    return bool(getattr(sys,'frozen',False)) or Path(sys.executable).resolve().parent == Path(app_dir).resolve()/'runtime'


def sync_desktop_icon(app_dir,plus,allow_elevation=False,folders=None):
    if os.name!='nt':return {'status':'unsupported'}
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    command=[str(powershell),'-NoProfile','-NonInteractive','-EncodedCommand',encoded_script(app_dir,plus,allow_elevation,folders)]
    result=subprocess.run(command,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    # Only the final JSON line is protocol output; PowerShell may emit type-loading messages.
    for line in reversed(result.stdout.decode('utf-8',errors='replace').splitlines()):
        if line.strip().startswith('{'):
            return json.loads(line)
    return {'status':'error','message':'Das Desktop-Symbol konnte nicht aktualisiert werden.'}
