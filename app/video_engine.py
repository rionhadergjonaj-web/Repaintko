"""Non-destructive video timeline, FFmpeg rendering and portable project files."""
from dataclasses import dataclass,field,asdict
from pathlib import Path
import copy,json,math,os,subprocess,tempfile,uuid

TRANSITIONS={'Keine':'none','Überblenden':'fade','Wischen links':'wipeleft','Wischen rechts':'wiperight','Wischen oben':'wipeup','Wischen unten':'wipedown','Schieben links':'slideleft','Schieben rechts':'slideright','Schieben oben':'slideup','Schieben unten':'slidedown','Kreis':'circlecrop','Rechteck':'rectcrop','Distanz':'distance','Durch Schwarz':'fadeblack','Durch Weiß':'fadewhite','Radial':'radial','Sanft links':'smoothleft','Sanft rechts':'smoothright','Sanft oben':'smoothup','Sanft unten':'smoothdown','Auflösen':'dissolve'}
EFFECTS={'Schwarzweiß':'hue=s=0','Sepia':'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131','Heller':'eq=brightness=0.15','Dunkler':'eq=brightness=-0.15','Kontrast':'eq=contrast=1.4','Kräftige Farben':'eq=saturation=1.6','Weichzeichnen':'gblur=sigma=6','Schärfen':'unsharp=5:5:1','Negativ':'negate','Horizontal spiegeln':'hflip','Vertikal spiegeln':'vflip','Warme Farben':'colorbalance=rs=.15:bs=-.1'}
KEYFRAMES={'Zoom':(1.,1.,4.),'Position X':(.5,0.,1.),'Position Y':(.5,0.,1.),'Helligkeit':(0.,-.8,.8),'Lautstärke':(1.,0.,2.)}

class Cancelled(Exception):pass

def binary(name):
    path=Path(__file__).parent/'video_tools'/f'{name}.exe'
    if not path.is_file():raise RuntimeError('Video-Werkzeuge fehlen. Bitte den Repaintko-Installer reparieren.')
    return str(path)

def run(args,cancel=None):
    with tempfile.TemporaryFile() as log:
        process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        while True:
            try:code=process.wait(timeout=.15);break
            except subprocess.TimeoutExpired:
                if cancel is not None and cancel.is_set():process.kill();process.wait();raise Cancelled('Abgebrochen')
        if code:
            log.seek(0);message=log.read().decode('utf-8',errors='replace')
            raise RuntimeError('Video-Verarbeitung fehlgeschlagen:\n'+message[-2200:])

def probe(path):
    path=str(Path(path).resolve())
    result=subprocess.run([binary('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',path],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Datei ist kein lesbares Video: '+Path(path).name)
    data=json.loads(result.stdout);video=next((s for s in data['streams'] if s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic')),None)
    if video is None:raise ValueError('Die Datei enthält keine Videospur.')
    duration=float(data.get('format',{}).get('duration') or video.get('duration') or 0)
    if not math.isfinite(duration) or duration<=0:raise ValueError('Die Videolänge konnte nicht bestimmt werden.')
    return {'path':path,'duration':duration,'audio':any(s['codec_type']=='audio' for s in data['streams']),'width':int(video['width']),'height':int(video['height'])}

@dataclass
class Clip:
    path:str
    source_duration:float
    audio:bool=True
    start:float=0.
    end:float=0.
    speed:float=1.
    volume:float=1.
    mute:bool=False
    transition:str='none'
    transition_duration:float=.5
    effects:list=field(default_factory=list)
    keyframes:dict=field(default_factory=dict)
    uid:str=field(default_factory=lambda:uuid.uuid4().hex)
    @property
    def duration(self):return (self.end-self.start)/self.speed
    @classmethod
    def from_file(cls,path):
        info=probe(path);return cls(info['path'],info['duration'],info['audio'],end=info['duration'])

def interpolate(points,t,default):
    points=sorted(points)
    if not points:return default
    if t<=points[0][0]:return points[0][1]
    for (a,x),(b,y) in zip(points,points[1:]):
        if t<=b:return x+(y-x)*(t-a)/(b-a)
    return points[-1][1]

def expression(points,default,var='t'):
    points=sorted(points)
    if not points:return str(default)
    expr=str(points[-1][1])
    for (a,x),(b,y) in reversed(list(zip(points,points[1:]))):expr=f'if(lt({var},{b}),{x}+({y-x})*({var}-{a})/({b-a}),{expr})'
    return f'if(lt({var},{points[0][0]}),{points[0][1]},{expr})'

class Timeline:
    def __init__(self):self.clips=[];self.width=1280;self.height=720;self.fps=30;self.history=[];self.future=[];self.path=None;self.saved=self.state()
    def state(self):return {'format':'Repaintko Video','version':1,'width':self.width,'height':self.height,'fps':self.fps,'clips':[asdict(c) for c in self.clips]}
    def restore(self,state):self.clips=[Clip(**c) for c in copy.deepcopy(state['clips'])];self.width=state['width'];self.height=state['height'];self.fps=state['fps']
    @property
    def dirty(self):return self.state()!=self.saved
    def remember(self):self.history.append(copy.deepcopy(self.state()));self.history=self.history[-100:];self.future.clear()
    def undo(self):
        if self.history:self.future.append(self.state());self.restore(self.history.pop())
    def redo(self):
        if self.future:self.history.append(self.state());self.restore(self.future.pop())
    def overlap(self,index):
        if index>=len(self.clips)-1 or self.clips[index].transition=='none':return 0.
        return min(self.clips[index].transition_duration,self.clips[index].duration/2,self.clips[index+1].duration/2)
    def starts(self):
        starts=[];position=0.
        for i,clip in enumerate(self.clips):starts.append(position);position+=clip.duration-self.overlap(i)
        return starts
    @property
    def duration(self):return sum(c.duration-self.overlap(i) for i,c in enumerate(self.clips))
    def locate(self,time):
        starts=self.starts()
        for i in reversed(range(len(starts))):
            if time>=starts[i]:return i,min(self.clips[i].duration,max(0,time-starts[i]))
        return (0,0.)
    def add(self,clips):
        if len(self.clips)+len(clips)>100:raise ValueError('Maximal 100 Clips pro Projekt.')
        self.remember();self.clips.extend(clips)
    def split(self,index,time):
        if len(self.clips)>=100:raise ValueError('Maximal 100 Clips pro Projekt.')
        clip=self.clips[index];local=time-self.starts()[index]
        if local<1/self.fps or local>clip.duration-1/self.fps:raise ValueError('Abspielkopf innerhalb des ausgewählten Clips platzieren, mindestens einen Frame vom Rand entfernt.')
        self.remember();left=copy.deepcopy(clip);right=copy.deepcopy(clip);right.uid=uuid.uuid4().hex
        left.end=clip.start+local*clip.speed;right.start=left.end;left.transition='none'
        left.effects=[];right.effects=[]
        for fx in clip.effects:
            if fx['start']<local:left.effects.append(dict(fx,end=min(fx['end'],local)))
            if fx['end']>local:right.effects.append(dict(fx,start=max(0,fx['start']-local),end=fx['end']-local))
        for name,points in clip.keyframes.items():
            value=interpolate(points,local,KEYFRAMES[name][0]);left.keyframes[name]=[p for p in points if p[0]<local]+[[local,value]];right.keyframes[name]=[[0,value]]+[[t-local,v] for t,v in points if t>local]
        self.clips[index:index+1]=[left,right]
    def trim(self,index,start,end,speed,volume,mute):
        c=self.clips[index]
        if not 0<=start<end<=c.source_duration+.001 or end-start<.04:raise ValueError('Ungültiger In/Out-Bereich.')
        if not .25<=speed<=4 or not 0<=volume<=2:raise ValueError('Ungültige Geschwindigkeit oder Lautstärke.')
        # Convert timed settings through source time, preserving their positions.
        old=copy.deepcopy(c);self.remember();c.start=start;c.end=end;c.speed=speed;c.volume=volume;c.mute=mute
        offset=(start-old.start)/old.speed;ratio=old.speed/speed
        c.effects=[dict(f,start=max(0,(f['start']-offset)*ratio),end=min(c.duration,(f['end']-offset)*ratio)) for f in old.effects if (f['end']-offset)*ratio>0 and (f['start']-offset)*ratio<c.duration]
        for name,points in old.keyframes.items():
            result=[[0,interpolate(points,offset,KEYFRAMES[name][0])],[c.duration,interpolate(points,offset+c.duration/ratio,KEYFRAMES[name][0])]]
            result.extend([[(t-offset)*ratio,v] for t,v in points if 0<(t-offset)*ratio<c.duration]);c.keyframes[name]=sorted(result)
    def validate(self,require_clips=True):
        if len(self.clips)>100 or (require_clips and not self.clips):raise ValueError('Bitte mindestens einen Clip hinzufügen (maximal 100).')
        if (self.width,self.height) not in ((640,360),(1280,720),(1920,1080),(3840,2160),(1080,1920)) or self.fps not in (24,25,30,50,60):raise ValueError('Ungültiges Ausgabeformat.')
        for c in self.clips:
            numbers=(c.source_duration,c.start,c.end,c.speed,c.volume,c.transition_duration)
            if not all(math.isfinite(float(x)) for x in numbers) or not 0<=c.start<c.end<=c.source_duration+.001 or not .25<=c.speed<=4 or not 0<=c.volume<=2:raise ValueError('Ungültige Clip-Einstellungen.')
            if c.transition not in TRANSITIONS.values() or not 0<=c.transition_duration<=5:raise ValueError('Ungültiger Übergang.')
            if not Path(c.path).is_file():raise ValueError('Quelldatei fehlt: '+c.path)
            for fx in c.effects:
                if fx['name'] not in EFFECTS or not 0<=fx['start']<fx['end']<=c.duration+.001:raise ValueError('Ungültiger Effektbereich.')
            for name,points in c.keyframes.items():
                if name not in KEYFRAMES:raise ValueError('Unbekannte Keyframe-Eigenschaft.')
                times=[p[0] for p in points]
                if len(set(times))!=len(times):raise ValueError('Doppelte Keyframe-Zeit.')
                for t,v in points:
                    if not math.isfinite(t) or not math.isfinite(v) or not 0<=t<=c.duration+.001 or not KEYFRAMES[name][1]<=v<=KEYFRAMES[name][2]:raise ValueError('Ungültiger Keyframe.')
    def save(self,path):
        self.validate(False);target=Path(path);data=self.state()
        for clip in data['clips']:
            try:clip['path']=os.path.relpath(clip['path'],target.parent)
            except ValueError:pass
        fd,temp=tempfile.mkstemp(dir=target.parent,suffix='.json');os.close(fd)
        try:Path(temp).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        self.path=str(target);self.saved=self.state()
    @classmethod
    def load(cls,path):
        if Path(path).stat().st_size>5_000_000:raise ValueError('Projektdatei ist zu groß.')
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('format')!='Repaintko Video' or data.get('version')!=1:raise ValueError('Unbekanntes Video-Projekt.')
        for c in data['clips']:c['path']=str((Path(path).parent/c['path']).resolve())
        result=cls();result.restore(data);result.validate(False);result.path=str(path);result.saved=result.state();return result

def clip_filter(clip,width,height,fps):
    filters=[f'setpts=(PTS-STARTPTS)/{clip.speed}',f'scale={width}:{height}:force_original_aspect_ratio=decrease',f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',f'fps={fps}','setsar=1','settb=AVTB']
    if any(k in clip.keyframes for k in ('Zoom','Position X','Position Y')):
        z=expression(clip.keyframes.get('Zoom',[]),1,'in_time');x=expression(clip.keyframes.get('Position X',[]),.5,'in_time');y=expression(clip.keyframes.get('Position Y',[]),.5,'in_time')
        filters.append(f"zoompan=z='{z}':x='(iw-iw/zoom)*({x})':y='(ih-ih/zoom)*({y})':d=1:s={width}x{height}:fps={fps}")
    if 'Helligkeit' in clip.keyframes:filters.append("eq=brightness='"+expression(clip.keyframes['Helligkeit'],0)+"':eval=frame")
    for effect in clip.effects:
        base=EFFECTS[effect['name']];separator=':' if '=' in base else '='
        filters.append(base+separator+f"enable='between(t,{effect['start']},{effect['end']})'")
    filters.append('format=yuv420p');return ','.join(filters)

def tempo_filters(speed):
    result=[]
    while speed<.5:result.append('atempo=0.5');speed/=.5
    while speed>2:result.append('atempo=2');speed/=2
    result.append(f'atempo={speed}');return ','.join(result)

def render(timeline,target,cancel,progress=lambda value,text:None,preview=False):
    timeline.validate();width,height,fps=(640,360,min(30,timeline.fps)) if preview else (timeline.width,timeline.height,timeline.fps)
    target=Path(target)
    if any(target.resolve()==Path(c.path).resolve() for c in timeline.clips):raise ValueError('Export darf keine Quelldatei überschreiben.')
    with tempfile.TemporaryDirectory(prefix='repaintko-video-') as folder:
        paths=[]
        for i,c in enumerate(timeline.clips):
            if cancel.is_set():raise Cancelled('Abgebrochen')
            progress(int(i/(len(timeline.clips)+1)*100),f'Clip {i+1} / {len(timeline.clips)}')
            path=Path(folder)/f'{i}.mp4';paths.append(path)
            args=[binary('ffmpeg'),'-hide_banner','-loglevel','error','-y','-threads','2','-ss',str(c.start),'-t',str(c.end-c.start),'-i',c.path]
            if not c.audio:args+=['-f','lavfi','-t',str(c.duration),'-i','anullsrc=r=48000:cl=stereo']
            volume=expression(c.keyframes.get('Lautstärke',[]),1)
            audio=(tempo_filters(c.speed)+',' if c.audio else '')+f"volume='{0 if c.mute else c.volume}*({volume})':eval=frame,aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={c.duration},asetpts=PTS-STARTPTS"
            args+=['-filter_threads','1','-vf',clip_filter(c,width,height,fps),'-map','0:v:0','-map','0:a:0' if c.audio else '1:a:0','-af',audio,'-t',str(c.duration),'-c:v','libx264','-preset','ultrafast' if preview else 'fast','-crf','23' if preview else '18','-threads','2','-c:a','aac','-b:a','192k',str(path)]
            run(args,cancel)
        progress(90,'Übergänge und Ton verbinden')
        args=[binary('ffmpeg'),'-hide_banner','-loglevel','error','-y','-threads','2']
        for path in paths:args+=['-threads','1','-i',str(path)]
        graph=[]
        for i in range(len(paths)):graph.extend([f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[v{i}]',f'[{i}:a]asetpts=PTS-STARTPTS[a{i}]'])
        video='v0';audio='a0';length=timeline.clips[0].duration
        for i in range(1,len(paths)):
            overlap=timeline.overlap(i-1);v=f'joinedv{i}';a=f'joineda{i}'
            if overlap:
                graph.append(f'[{video}][v{i}]xfade=transition={timeline.clips[i-1].transition}:duration={overlap}:offset={length-overlap}[{v}]')
                graph.append(f'[{audio}][a{i}]acrossfade=d={overlap}:c1=tri:c2=tri[{a}]')
            else:
                graph.append(f'[{video}][v{i}]concat=n=2:v=1:a=0[{v}]');graph.append(f'[{audio}][a{i}]concat=n=2:v=0:a=1[{a}]')
            video=v;audio=a;length+=timeline.clips[i].duration-overlap
        # Output beside the target allows an atomic replacement on the same volume.
        fd,temp=tempfile.mkstemp(dir=target.parent,suffix='.mp4');os.close(fd)
        try:
            args+=['-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map',f'[{video}]','-map',f'[{audio}]','-c:v','libx264','-preset','ultrafast' if preview else 'fast','-crf','23' if preview else '18','-threads','2','-pix_fmt','yuv420p','-r',str(fps),'-c:a','aac','-b:a','192k','-movflags','+faststart',temp]
            run(args,cancel)
            if cancel.is_set():raise Cancelled('Abgebrochen')
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        progress(100,'Fertig')
