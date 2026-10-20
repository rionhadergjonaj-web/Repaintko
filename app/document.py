"""Image document, independent of any GUI framework."""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageChops, ImageColor
from layers import Layers, layer
from censor import censor_segment, StrokeCache

MAX_PIXELS = 64_000_000
HISTORY_BUDGET = 480_000_000  # Three times the previous 160 MB history budget.
DEFAULT_SIZE = (2560, 1440)
PRESETS = {'Full HD': (1920, 1080), 'QHD': DEFAULT_SIZE, '4K': (3840, 2160), '8K': (7680, 4320)}


def checked_size(w, h):
    if w < 1 or h < 1 or w*h > MAX_PIXELS:
        raise ValueError('Die Größe muss positiv sein und darf 64 Millionen Pixel nicht überschreiten.')
    return w, h


def load_image(path):
    with Image.open(path) as source:
        checked_size(*source.size)
        oriented=ImageOps.exif_transpose(source)
        return oriented.convert('RGBA' if 'A' in oriented.getbands() or 'transparency' in oriented.info else 'RGB')


class Document(Layers):
    def __init__(self, size=DEFAULT_SIZE):
        self.layers=[layer(Image.new('RGBA', checked_size(*size)),'Hintergrund')]
        self.active=0
        self.layers[0]['paper_color']='#ffffff'
        self.path = None
        self.revision = self.saved_revision = self.next_revision = 0
        self.effect_base = None
        self.effect_stack = ()
        self.history, self.future = [], []
        self.selection = self.clipboard = None
        self.stroke_source = self.stroke_base = None
        self.stroke_cache = self.base_cache = None
        self.stroke_mask = None

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    def snapshot(self, copy=True):
        return (self.image, self.revision, self.effect_base, self.effect_stack,
                [dict(entry) for entry in self.layers],self.active)

    def remember(self, kind='edit'):
        self.history.append(self.snapshot())
        while len(self.history)>1 and sum(s[0].width*s[0].height*4 for s in self.history)>HISTORY_BUDGET:
            self.history.pop(0)
        self.future.clear()
        if kind!='layer':self.image=self.image.copy()
        if self.effect_base is not None and kind == 'edit':
            self.image = self.effect_base.copy()
            self.effect_base, self.effect_stack = None, ()
        elif self.effect_base is not None and kind == 'censor':
            self.effect_base = self.effect_base.copy()
        self.next_revision += 1
        self.revision = self.next_revision

    def undo(self):
        if self.history:
            self.future.append(self.snapshot(False))
            _, self.revision, _, _, self.layers,self.active = self.history.pop()
            self.selection = None

    def redo(self):
        if self.future:
            self.history.append(self.snapshot(False))
            _, self.revision, _, _, self.layers,self.active = self.future.pop()
            self.selection = None

    def open(self, path):
        if Path(path).suffix.lower()in ('.repainko','.repaintko'):
            size,layers,active=self.read_project(path)
            self.__init__(size);self.layers,self.active,self.path=layers,active,str(path)
            return
        image = load_image(path)
        self.__init__(image.size)
        self.image, self.path = image, str(path)

    def save(self, path, as_copy=False, transparent=False):
        target = Path(path)
        if as_copy and self.path and target.resolve() == Path(self.path).resolve():
            raise ValueError('Bitte für die Kopie einen anderen Dateinamen wählen.')
        project=target.suffix.lower()in ('.repainko','.repaintko')
        if project:self.save_project(target)
        else:
            supports_alpha=target.suffix.lower() in ('.png','.webp','.tif','.tiff')
            if transparent and not supports_alpha:raise ValueError('Transparenz benötigt PNG, WebP oder TIFF. Bitte einen dieser Dateitypen wählen.')
            exported=self.composite(transparent=supports_alpha if transparent is None else transparent,preserve_alpha=supports_alpha)
            if exported.mode=='RGBA' and exported.getchannel('A').getextrema()==(255,255):exported=exported.convert('RGB')
            exported.save(target)
        if not as_copy and (project or len(self.layers)==1):
            self.path, self.saved_revision = str(target), self.revision

    def apply_stack(self, result, stack):
        if result.size != self.image.size or len({e[0] for e in stack}) != len(stack):
            raise ValueError('Ungültige Effektkombination.')
        base = self.effect_base if self.effect_base is not None else self.image.copy()
        self.remember('effect')
        if self.image.mode=='RGBA':
            result=result.convert('RGBA');result.putalpha(self.image.getchannel('A'))
        self.effect_base, self.effect_stack, self.image = base, tuple(stack), result

    def begin_stroke(self, tool):
        self.selection = None
        self.remember('censor' if tool in ('Zensur','Radierer') else 'edit')
        if tool=='Radierer':
            if self.image.mode!='RGBA':self.image=self.image.convert('RGBA')
            if self.effect_base is not None and self.effect_base.mode!='RGBA':self.effect_base=self.effect_base.convert('RGBA')
        self.stroke_source, self.stroke_base = self.history[-1][0], self.history[-1][2]
        if tool not in ('Zensur','Radierer') and self.stroke_base is not None:self.stroke_source=self.stroke_base
        self.stroke_cache, self.base_cache = StrokeCache(), StrokeCache()
        self.stroke_mask=Image.new('L',self.image.size) if tool!='Zensur' else None
        self.censor_source=(self.stroke_source if self.stroke_source.mode=='RGB' else self.stroke_source.convert('RGB')) if tool=='Zensur' else None
        self.censor_base=(self.stroke_base if self.stroke_base.mode=='RGB' else self.stroke_base.convert('RGB')) if tool=='Zensur' and self.stroke_base is not None else None

    def stroke(self, a, b, tool, color, background, width, mode='Verpixeln', strength=18, opacity=100):
        if tool == 'Zensur':
            args = (a, b, width, mode, strength)
            bounds = censor_segment(self.image, self.censor_source, *args, cache=self.stroke_cache)
            if self.image.mode=='RGBA':
                patch=self.image.crop(bounds);patch.putalpha(self.stroke_source.crop(bounds).getchannel('A'));self.image.paste(patch,bounds[:2])
            if self.effect_base is not None:
                censor_segment(self.effect_base, self.censor_base, *args, cache=self.base_cache)
                if self.effect_base.mode=='RGBA':
                    patch=self.effect_base.crop(bounds);patch.putalpha(self.stroke_base.crop(bounds).getchannel('A'));self.effect_base.paste(patch,bounds[:2])
            return bounds
        pen = ImageDraw.Draw(self.stroke_mask)
        width = max(1,int(width))
        color = background if tool == 'Radierer' else color
        if tool == 'Füller':
            # A fixed, angled broad nib: connected swept polygons avoid gaps
            # even when pointer events arrive far apart during fast strokes.
            half=max(.5,(width-1)/2);thin=max(.5,width*.10)
            dx=half*.7071;dy=-half*.7071;tx=thin*.7071;ty=thin*.7071
            corners=[(-dx-tx,-dy-ty),(dx-tx,dy-ty),(dx+tx,dy+ty),(-dx+tx,-dy+ty)]
            first=[(a[0]+x,a[1]+y) for x,y in corners]
            last=[(b[0]+x,b[1]+y) for x,y in corners]
            pen.polygon(first,fill=255);pen.polygon(last,fill=255)
            for i in range(4):
                j=(i+1)%4;pen.polygon([first[i],first[j],last[j],last[i]],fill=255)
        elif tool == 'Airbrush':
            steps = max(1, math.ceil(math.dist(a, b)/max(2, width/2)))
            for step in range(1, steps+1):
                x, y = a[0]+(b[0]-a[0])*step/steps, a[1]+(b[1]-a[1])*step/steps
                for _ in range(max(12, width*2)):
                    angle, r = random.random()*math.tau, math.sqrt(random.random())*width
                    pen.point((round(x+math.cos(angle)*r), round(y+math.sin(angle)*r)), fill=255)
        else:
            pen.line([a, b], fill=255, width=width)
            if width > 1:
                r = (width-1)/2
                for x, y in (a, b):
                    pen.ellipse((x-r, y-r, x+r, y+r), fill=255)
        box=(max(0,min(a[0],b[0])-width-2),max(0,min(a[1],b[1])-width-2),
             min(self.image.width,max(a[0],b[0])+width+2),min(self.image.height,max(a[1],b[1])+width+2))
        mask=self.stroke_mask.crop(box).point([round(v*max(0,min(100,opacity))/100) for v in range(256)])
        original=self.stroke_source.crop(box).convert('RGBA')
        if tool=='Radierer' and self.image.mode=='RGBA':
            original.putalpha(ImageChops.multiply(original.getchannel('A'),ImageOps.invert(mask)))
            result=original
        else:
            paint=Image.new('RGBA',original.size,ImageColor.getrgb(color)+(255,));paint.putalpha(mask)
            result=Image.alpha_composite(original,paint)
        self.image.paste(result.convert(self.image.mode),box[:2])
        if tool=='Radierer' and self.effect_base is not None:
            base=self.stroke_base.crop(box).convert('RGBA')
            base.putalpha(ImageChops.multiply(base.getchannel('A'),ImageOps.invert(mask)))
            self.effect_base.paste(base,box[:2])
        return box

    def finish_stroke(self):
        self.stroke_source = self.stroke_base = None
        self.stroke_cache = self.base_cache = None
        self.stroke_mask=self.censor_source=self.censor_base=None

    def shape(self, tool, a, b, color, background, width, fill_mode, points=None):
        self.remember()
        pen = ImageDraw.Draw(self.image)
        fill = None if fill_mode == 'Nur Kontur' else background
        outline = None if fill_mode == 'Nur Füllung' else color
        if fill_mode == 'Nur Füllung': fill = color
        box = (min(a[0],b[0]), min(a[1],b[1]), max(a[0],b[0]), max(a[1],b[1]))
        if tool == 'Linie': pen.line([a,b], fill=color, width=width)
        elif tool == 'Rechteck': pen.rectangle(box, fill=fill, outline=outline, width=width)
        elif tool == 'Rundrechteck': pen.rounded_rectangle(box, radius=min(20,(box[2]-box[0])/4,(box[3]-box[1])/4), fill=fill, outline=outline, width=width)
        elif tool == 'Ellipse': pen.ellipse(box, fill=fill, outline=outline, width=width)
        else:
            pts = points or [((box[0]+box[2])/2,box[1]), (box[2],box[3]), (box[0],box[3])]
            pen.polygon(pts, fill=fill)
            if outline: pen.line(pts+[pts[0]], fill=outline, width=width, joint='curve')

    def copy(self):
        self.clipboard = self.image.crop(self.selection) if self.selection else self.image.copy()

    def delete(self, color):
        if self.selection:
            self.remember()
            x,y,r,b = self.selection
            ImageDraw.Draw(self.image).rectangle((x,y,r-1,b-1), fill=(0,0,0,0) if self.image.mode=='RGBA' else color)
            self.selection = None

    @property
    def paper_color(self):
        return self.layers[0].get('paper_color','#ffffff')

    @property
    def paper_opacity(self):
        return self.layers[0].get('paper_opacity',100)

    def set_paper_opacity(self,value):
        value=max(0,min(100,int(value)))
        if value!=self.paper_opacity:
            self.remember('layer')
            self.layers[0]['paper_opacity']=value

    def set_paper_color(self,color):
        ImageColor.getrgb(color)
        self.remember('layer')
        self.layers[0]['paper_color']=color

    def prepare_import(self,image,upscale=False):
        checked_size(*image.size)
        count=len(self.layers)+1
        if count>32:raise ValueError('Maximal 32 Ebenen. Bitte zuerst eine Ebene entfernen oder zusammenführen.')
        for factor in ((4,2,1) if upscale else (1,)):
            size=tuple(max(1,math.floor(v*math.sqrt(factor))) for v in image.size)
            canvas=(max(size[0],self.image.width),max(size[1],self.image.height))
            if canvas[0]*canvas[1]<=min(MAX_PIXELS,128_000_000//count):
                return image.resize(size,Image.Resampling.LANCZOS) if size!=image.size else image
        raise ValueError('Das Bild überschreitet die Grenze von 64 Millionen Leinwandpixeln oder 128 Millionen Ebenenpixeln.')

    def paste(self,image=None,upscale=False,position=(0,0),name='Eingefügtes Bild'):
        image=image if image is not None else self.clipboard
        if image is None:return
        image=self.prepare_import(image,upscale)
        x,y=map(int,position)
        if x<0 or y<0:raise ValueError('Die Position muss innerhalb des Blatts liegen.')
        canvas=checked_size(max(self.image.width,x+image.width),max(self.image.height,y+image.height))
        if canvas[0]*canvas[1]*(len(self.layers)+1)>128_000_000:
            raise ValueError('Diese Position überschreitet die Grenze von 128 Millionen Ebenenpixeln.')
        # Allocate everything before touching the document; old layer pixels and effects stay intact.
        entries=[dict(entry) for entry in self.layers]
        if canvas!=self.image.size:
            for entry in entries:
                for key in ('image','base'):
                    source=entry[key]
                    if source is None:continue
                    expanded=Image.new('RGBA',canvas);expanded.paste(source,(0,0));entry[key]=expanded
        inserted=Image.new('RGBA',canvas);inserted.paste(image.convert('RGBA'),(x,y))
        entries.append(layer(inserted,name))
        self.remember('layer');self.layers=entries;self.active=len(entries)-1
        self.selection=(x,y,x+image.width,y+image.height)

    def move_selection(self, box, x, y, background):
        self.remember()
        tile = self.image.crop(box)
        ImageDraw.Draw(self.image).rectangle((box[0],box[1],box[2]-1,box[3]-1), fill=(0,0,0,0) if self.image.mode=='RGBA' else background)
        if self.image.mode=='RGBA':self.image.alpha_composite(tile,(x,y))
        else:self.image.paste(tile,(x,y))
        self.selection = (x,y,x+tile.width,y+tile.height)

    def apply_removal(self,result):
        if result.size!=self.image.size:raise ValueError('Die Ergebnisgröße passt nicht zur Ebene.')
        if len(self.layers)>=32 or self.image.width*self.image.height*(len(self.layers)+1)>128_000_000:
            raise ValueError('Für das Original und das Ergebnis ist keine weitere Ebene frei (maximal 32 Ebenen / 128 Millionen Ebenenpixel).')
        original=self.layers[self.active]
        entry=layer(result,original['name']+' · Entfernt')
        entry['opacity']=original['opacity']
        self.remember('layer')
        self.layers[self.active]['visible']=False
        self.layers.insert(self.active+1,entry);self.active+=1;self.selection=None

    def resize(self, size, canvas=False, background='white'):
        checked_size(*size)
        if size[0]*size[1]*len(self.layers)>128_000_000:raise ValueError('Maximal 128 Millionen Ebenenpixel insgesamt.')
        self.remember('layer')
        for entry in self.layers:
            for key in ('image','base'):
                image=entry[key]
                if image is None:continue
                if canvas:
                    new=Image.new(image.mode,size,(0,0,0,0) if image.mode=='RGBA' else background)
                    new.paste(image,(0,0));entry[key]=new
                else:entry[key]=image.resize(size,Image.Resampling.LANCZOS)
            entry['base']=None;entry['stack']=()
        self.selection = None

    def crop(self):
        if self.selection:
            self.remember('layer')
            for entry in self.layers:
                entry['image']=entry['image'].crop(self.selection);entry['base']=None;entry['stack']=()
            self.selection = None

    def transform(self, key):
        if not self.selection and key in ('right','left','flip','mirror'):
            self.remember('layer')
            method={'right':Image.Transpose.ROTATE_270,'left':Image.Transpose.ROTATE_90,
                    'flip':Image.Transpose.FLIP_TOP_BOTTOM,'mirror':Image.Transpose.FLIP_LEFT_RIGHT}[key]
            for entry in self.layers:
                entry['image']=entry['image'].transpose(method);entry['base']=None;entry['stack']=()
            return
        self.remember()
        source = self.image.crop(self.selection) if self.selection else self.image
        funcs = {'right': lambda i:i.transpose(Image.Transpose.ROTATE_270), 'left':lambda i:i.transpose(Image.Transpose.ROTATE_90),
                 'flip':ImageOps.flip, 'mirror':ImageOps.mirror,'invert':ImageOps.invert,'gray':lambda i:ImageOps.grayscale(i).convert('RGB')}
        result = funcs[key](source.convert('RGB'))
        if source.mode=='RGBA':
            alpha=source.getchannel('A')
            if key in ('right','left','flip','mirror'):alpha=funcs[key](alpha)
            result=result.convert('RGBA');result.putalpha(alpha)
        if self.selection: self.image.paste(result,self.selection[:2])
        else: self.image = result
        self.selection = None
