"""Editable animation frames and atomic GIF export."""
import os
import tempfile
from pathlib import Path
from PIL import Image, ImageOps
from document import Document, load_image

MAX_FRAMES=200
MAX_FRAME_PIXELS=128_000_000

def clone_document(source):
    result=Document(source.image.size)
    result.layers=[dict(entry,image=entry['image'].copy(),base=entry['base'].copy() if entry['base'] is not None else None) for entry in source.layers]
    result.active=source.active
    return result

class Animation:
    def __init__(self,source):
        self.frames=[clone_document(source)];self.index=0;self.fps=10;self.path=None;self.saved=None
        self.frames[0].layers[0]['paper_opacity']=0
    def signature(self):return (self.fps,tuple((id(frame),frame.revision) for frame in self.frames))
    @property
    def dirty(self):return self.saved!=self.signature()
    def check_capacity(self,document):
        pixels=sum(f.image.width*f.image.height*len(f.layers) for f in self.frames)+document.image.width*document.image.height*len(document.layers)
        if len(self.frames)>=MAX_FRAMES or pixels>MAX_FRAME_PIXELS:raise ValueError('Maximal 200 Frames und insgesamt 128 Millionen Ebenenpixel pro Animation.')
    def add(self,duplicate=False,path=None):
        current=self.frames[self.index]
        if duplicate:frame=clone_document(current)
        else:
            frame=Document(self.frames[0].image.size)
            frame.layers[0]['paper_color']=current.paper_color;frame.layers[0]['paper_opacity']=0
            if path:
                image=ImageOps.contain(load_image(path).convert('RGBA'),frame.image.size)
                frame.image.alpha_composite(image,((frame.image.width-image.width)//2,(frame.image.height-image.height)//2))
        self.check_capacity(frame);self.index+=1;self.frames.insert(self.index,frame)
    def remove(self):
        if len(self.frames)==1:raise ValueError('Eine Animation benötigt mindestens einen Frame.')
        self.frames.pop(self.index);self.index=min(self.index,len(self.frames)-1)
    def move(self,offset):
        target=self.index+offset
        if 0<=target<len(self.frames):self.frames[self.index],self.frames[target]=self.frames[target],self.frames[self.index];self.index=target
    def durations(self):
        # GIF uses centiseconds. Distribute rounding error across frames.
        return [max(10,(round((i+1)*100/self.fps)-round(i*100/self.fps))*10) for i in range(len(self.frames))]
    def export(self,path,transparent=False):
        if not 1<=self.fps<=50:raise ValueError('FPS muss zwischen 1 und 50 liegen.')
        size=self.frames[0].image.size
        if any(frame.image.size!=size for frame in self.frames):raise ValueError('Alle Frames müssen dieselbe Größe haben. Bitte über Bild → Größe ändern angleichen.')
        pixels=sum(f.image.width*f.image.height*len(f.layers) for f in self.frames)
        if pixels>MAX_FRAME_PIXELS:raise ValueError('Die Animation überschreitet 128 Millionen Ebenenpixel.')
        images=[]
        for frame in self.frames:
            image=frame.composite(transparent=transparent,preserve_alpha=True).convert('RGBA')
            indexed=image.convert('RGB').quantize(colors=255,method=Image.Quantize.MEDIANCUT)
            indexed.paste(255,mask=image.getchannel('A').point(lambda a:255 if a<128 else 0))
            indexed.info['transparency']=255;images.append(indexed)
        target=Path(path);fd,temp=tempfile.mkstemp(dir=target.parent,suffix='.gif');os.close(fd)
        try:
            images[0].save(temp,format='GIF',save_all=True,append_images=images[1:],duration=self.durations(),loop=0,disposal=2,transparency=255,optimize=False)
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        self.path=str(target);self.saved=self.signature()
