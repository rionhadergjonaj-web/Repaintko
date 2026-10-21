"""Read Spotify's local Windows media session; no login or network."""
import base64
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QSizePolicy, QPushButton, QStyle

SCRIPT = r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$managerType=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
$mediaType=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties,Windows.Media.Control,ContentType=WindowsRuntime]
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1)
function Await($operation,$type) {
    $task=$asTask.MakeGenericMethod($type).Invoke($null,@($operation))
    if (-not $task.Wait(4000)) { throw 'Media request timed out' }
    return $task.Result
}
$manager=$null
while ($true) {
    if ($ownerId -and -not (Get-Process -Id $ownerId -ErrorAction SilentlyContinue)) { break }
    try {
        if ($null -eq $manager) { $manager=Await ($managerType::RequestAsync()) $managerType }
        $sessions=@($manager.GetSessions() | Where-Object { $_.SourceAppUserModelId -match '(?i)spotify' })
        $session=$sessions | Where-Object { $_.GetPlaybackInfo().PlaybackStatus.ToString() -eq 'Playing' } | Select-Object -First 1
        if ($null -eq $session) { $session=$sessions | Select-Object -First 1 }
        if ($null -eq $session) { $data=@{active=$false} }
        else {
            $media=Await ($session.TryGetMediaPropertiesAsync()) $mediaType
            $timeline=$session.GetTimelineProperties();$info=$session.GetPlaybackInfo()
            $playing=$info.PlaybackStatus.ToString() -eq 'Playing'
            $position=($timeline.Position-$timeline.StartTime).TotalSeconds
            $duration=($timeline.EndTime-$timeline.StartTime).TotalSeconds
            $rate=1.0;if ($null -ne $info.PlaybackRate) { $rate=[double]$info.PlaybackRate }
            if ($playing -and $timeline.LastUpdatedTime.Year -gt 2000) { $position+=[Math]::Max(0,([DateTimeOffset]::UtcNow-$timeline.LastUpdatedTime).TotalSeconds)*$rate }
            $data=@{active=![string]::IsNullOrWhiteSpace($media.Title);title=$media.Title;artist=$media.Artist;playing=$playing;position=$position;duration=$duration;rate=$rate;source=$session.SourceAppUserModelId}
        }
        [Console]::WriteLine(($data | ConvertTo-Json -Compress))
    } catch { $manager=$null;[Console]::WriteLine('{"active":false,"unavailable":true}') }
    Start-Sleep -Milliseconds 2000
}
'''

CONTROL_SCRIPT = SCRIPT.split('$manager=$null')[0] + r"""
try {
    $manager=Await ($managerType::RequestAsync()) $managerType
    $session=$manager.GetSessions() | Where-Object { $_.SourceAppUserModelId -match '(?i)spotify' -and $_.SourceAppUserModelId -eq $request.source } | Select-Object -First 1
    if ($null -eq $session) { throw 'Spotify session no longer available' }
    switch ($request.command) {
        'previous' { $operation=$session.TrySkipPreviousAsync() }
        'toggle' { $operation=$session.TryTogglePlayPauseAsync() }
        'next' { $operation=$session.TrySkipNextAsync() }
        default { throw 'Unknown command' }
    }
    $ok=Await $operation ([bool])
    [Console]::WriteLine((@{ok=[bool]$ok} | ConvertTo-Json -Compress))
} catch { [Console]::WriteLine('{"ok":false}') }
"""


def send_control(command,source):
    if command not in ('previous','toggle','next') or 'spotify' not in source.lower():return False
    payload=base64.b64encode(json.dumps(dict(command=command,source=source)).encode()).decode()
    script="$request=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+payload+"'))|ConvertFrom-Json;"+CONTROL_SCRIPT
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=12)
    return bool(json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1]).get('ok'))

class SpotifyMonitor(QObject):
    changed=Signal(dict)
    commandFinished=Signal(bool)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=None;self.stopped=threading.Event();self.command_lock=threading.Lock();self.source=""
    def start(self):
        if os.name!='nt' or self.process is not None or self.stopped.is_set():return
        command=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        try:
            self.process=subprocess.Popen([str(command),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode((f'$ownerId={os.getpid()};\n'+SCRIPT).encode('utf-16le')).decode('ascii')],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError:return
        threading.Thread(target=self.read,daemon=True).start()
    def read(self):
        process=self.process
        try:
            for line in process.stdout:
                if self.stopped.is_set():break
                try:
                    data=json.loads(line.decode('utf-8'));self.source=data.get('source','');self.changed.emit(data)
                except (ValueError,RuntimeError):continue
        finally:
            process.stdout.close()
            if not self.stopped.is_set():self.changed.emit({'active':False})
    def command(self,name):
        if self.stopped.is_set() or not self.command_lock.acquire(False):
            self.commandFinished.emit(False);return
        source=self.source
        def run():
            ok=False
            try:ok=send_control(name,source)
            except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):pass
            finally:
                self.command_lock.release()
                if not self.stopped.is_set():self.commandFinished.emit(ok)
        threading.Thread(target=run,daemon=True).start()

    def stop(self):
        self.stopped.set()
        if self.process is not None and self.process.poll() is None:self.process.terminate()


def clock_text(seconds):
    seconds=max(0,int(seconds));return f'{seconds//60}:{seconds%60:02d}'

class SpotifyWidget(QWidget):
    activeChanged=Signal(bool)
    commandRequested=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.data={};self.received=0
        self.setMinimumWidth(160);self.setMaximumWidth(460);self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        layout=QVBoxLayout(self);layout.setContentsMargins(8,3,8,3);layout.setSpacing(2)
        self.title=QLabel();self.title.setAlignment(Qt.AlignmentFlag.AlignCenter);self.title.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.title)
        row=QHBoxLayout();self.elapsed=QLabel('0:00');self.total=QLabel('0:00')
        self.bar=QProgressBar();self.bar.setRange(0,1000);self.bar.setTextVisible(False);self.bar.setFixedHeight(5)
        self.bar.setStyleSheet('QProgressBar {background:#45505c;border:0;border-radius:2px;} QProgressBar::chunk {background:#1ed760;border-radius:2px;}')
        row.addWidget(self.elapsed);row.addWidget(self.bar,1);row.addWidget(self.total);layout.addLayout(row)
        controls=QHBoxLayout();controls.setSpacing(4);controls.addStretch()
        self.buttons={}
        for name,label,tip in (('previous','⏮','Vorheriger Titel'),('toggle','▶','Wiedergabe / Pause'),('next','⏭','Nächster Titel')):
            button=QPushButton();button.setIcon(self.style().standardIcon({'previous':QStyle.StandardPixmap.SP_MediaSkipBackward,'toggle':QStyle.StandardPixmap.SP_MediaPlay,'next':QStyle.StandardPixmap.SP_MediaSkipForward}[name]));button.setFixedSize(32,24);button.setToolTip(tip);button.setAccessibleName(tip)
            button.clicked.connect(lambda checked=False,n=name:self.request(n));controls.addWidget(button);self.buttons[name]=button
        controls.addStretch();layout.addLayout(controls)
        self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self.tick)
    def request(self,name):
        if not self.data.get('active'):return
        for button in self.buttons.values():button.setEnabled(False)
        self.commandRequested.emit(name)
    def command_finished(self,ok):
        for button in self.buttons.values():button.setEnabled(bool(self.data.get('active')))
        self.setToolTip('' if ok else 'Spotify konnte den Befehl nicht ausführen. Bitte erneut versuchen.')

    def receive(self,data):
        self.data=data;self.received=time.monotonic();active=bool(data.get('active'))
        self.activeChanged.emit(active)
        self.buttons['toggle'].setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause if data.get('playing') else QStyle.StandardPixmap.SP_MediaPlay))
        if active:self.timer.start();self.tick()
        else:self.timer.stop();self.title.clear();self.bar.setValue(0)
    def tick(self):
        data=self.data
        if not data.get('active'):return
        if time.monotonic()-self.received>12:self.receive({'active':False});return
        duration=max(0,float(data.get('duration',0)));position=max(0,float(data.get('position',0)))
        if data.get('playing'):position+=(time.monotonic()-self.received)*max(0,float(data.get('rate',1)))
        if duration:position=min(position,duration)
        text='Spotify · '+str(data.get('title',''))
        if data.get('artist'):text+=' — '+str(data['artist'])
        if not data.get('playing'):text+=' · Pausiert'
        self.title.setToolTip(text);self.title.setText(self.title.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,max(20,self.width()-20)))
        self.elapsed.setText(clock_text(position));self.total.setText(clock_text(duration) if duration else '–:––')
        self.bar.setValue(round(position/duration*1000) if duration else 0)
