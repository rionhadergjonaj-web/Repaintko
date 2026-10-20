"""Layer composition and lossless Repainko project files."""
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from PIL import Image, ImageColor


def layer(image, name):
    return dict(image=image,name=name,visible=True,opacity=100,base=None,stack=())


class Layers:
    @property
    def image(self): return self.layers[self.active]['image']
    @image.setter
    def image(self,value): self.layers[self.active]['image']=value
    @property
    def effect_base(self): return self.layers[self.active]['base']
    @effect_base.setter
    def effect_base(self,value): self.layers[self.active]['base']=value
    @property
    def effect_stack(self): return self.layers[self.active]['stack']
    @effect_stack.setter
    def effect_stack(self,value): self.layers[self.active]['stack']=value

    def composite(self, box=None, transparent=False, preserve_alpha=False):
        size=self.image.size if box is None else (box[2]-box[0],box[3]-box[1])
        visible=[entry for entry in self.layers if entry['visible'] and entry['opacity']>0]
        if len(visible)==1 and visible[0]['opacity']==100 and visible[0]['image'].mode=='RGB' and not transparent:
            image=visible[0]['image']
            return image.crop(box) if box else image
        output=Image.new('RGBA',size,(0,0,0,0) if transparent else (*ImageColor.getrgb(self.paper_color)[:3],round(self.paper_opacity*255/100)))
        for entry in visible:
            image=entry['image'].crop(box) if box else entry['image']
            image=image.convert('RGBA')
            if entry['opacity']!=100:
                image.putalpha(image.getchannel('A').point([round(x*entry['opacity']/100) for x in range(256)]))
            output=Image.alpha_composite(output,image)
        if transparent or preserve_alpha:return output
        background=Image.new('RGBA',size,'white')
        return Image.alpha_composite(background,output).convert('RGB')

    def add_layer(self,name=None):
        if len(self.layers)>=32 or self.image.width*self.image.height*(len(self.layers)+1)>128_000_000:
            raise ValueError('Maximal 32 Ebenen und insgesamt 128 Millionen Ebenenpixel.')
        self.remember('layer')
        self.layers.insert(self.active+1,layer(Image.new('RGBA',self.image.size),name or f'Ebene {len(self.layers)+1}'))
        self.active+=1

    def duplicate_layer(self):
        if len(self.layers)>=32 or self.image.width*self.image.height*(len(self.layers)+1)>128_000_000:
            raise ValueError('Maximal 32 Ebenen und insgesamt 128 Millionen Ebenenpixel.')
        self.remember('layer')
        entry=dict(self.layers[self.active]);entry['image']=self.image.copy();entry['name']+=' – Kopie'
        self.layers.insert(self.active+1,entry);self.active+=1

    def remove_layer(self):
        if len(self.layers)==1:raise ValueError('Mindestens eine Ebene muss bestehen bleiben.')
        paper=self.paper_color;opacity=self.paper_opacity
        self.remember('layer');self.layers.pop(self.active);self.layers[0]['paper_color']=paper;self.layers[0]['paper_opacity']=opacity;self.active=min(self.active,len(self.layers)-1)

    def move_layer(self,offset):
        target=self.active+offset
        if 0<=target<len(self.layers):
            paper=self.paper_color;opacity=self.paper_opacity
            self.remember('layer');self.layers[self.active],self.layers[target]=self.layers[target],self.layers[self.active];self.active=target
            self.layers[0]['paper_color']=paper;self.layers[0]['paper_opacity']=opacity

    def set_layer(self, key, value, index=None):
        index=self.active if index is None else index
        if key=='name':value=str(value).strip()[:100] or 'Ebene'
        elif key=='opacity':value=max(0,min(100,int(value)))
        elif key=='visible':value=bool(value)
        else:raise ValueError('Unbekannte Ebeneneigenschaft')
        if self.layers[index][key]!=value:
            self.remember('layer');self.layers[index][key]=value

    def merge_down(self):
        if self.active==0:return
        if not all(self.layers[i]['visible'] for i in (self.active-1,self.active)):
            raise ValueError('Zum Zusammenführen beide Ebenen sichtbar schalten.')
        paper=self.paper_color;opacity=self.paper_opacity
        self.remember('layer')
        below,above=self.layers[self.active-1:self.active+1]
        def pixels(entry):
            image=entry['image'].convert('RGBA')
            image.putalpha(image.getchannel('A').point([round(x*entry['opacity']/100) for x in range(256)]))
            return image
        self.layers[self.active-1:self.active+1]=[layer(Image.alpha_composite(pixels(below),pixels(above)),below['name'])]
        self.active-=1
        self.layers[0]['paper_color']=paper;self.layers[0]['paper_opacity']=opacity

    def save_project(self,path):
        manifest={'format':'Repainko','version':1,'size':list(self.image.size),'active':self.active,'layers':[]}
        fd,temporary=tempfile.mkstemp(prefix='.repainko-',suffix='.tmp',dir=Path(path).parent)
        os.close(fd)
        try:
            with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
                for index,entry in enumerate(self.layers):
                    record={key:entry[key] for key in ('name','visible','opacity','stack')}
                    if 'paper_color' in entry:record['paper_color']=entry['paper_color']
                    if 'paper_opacity' in entry:record['paper_opacity']=entry['paper_opacity']
                    for key in ('image','base'):
                        if entry[key] is not None:
                            stream=io.BytesIO();entry[key].save(stream,'PNG')
                            name=f'layers/{index}-{key}.png';archive.writestr(name,stream.getvalue());record[key]=name
                    manifest['layers'].append(record)
                archive.writestr('project.json',json.dumps(manifest,ensure_ascii=False))
            os.replace(temporary,path)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)

    @staticmethod
    def read_project(path):
        from document import checked_size
        from effects import EFFECTS
        with zipfile.ZipFile(path) as archive:
            if archive.getinfo('project.json').file_size>1_000_000:raise ValueError('Projektbeschreibung zu groß.')
            manifest=json.loads(archive.read('project.json'))
            if manifest.get('format')!='Repainko' or manifest.get('version')!=1:raise ValueError('Unbekanntes Projektformat.')
            size=checked_size(*manifest['size']);records=manifest['layers']
            if not 1<=len(records)<=32 or size[0]*size[1]*len(records)>128_000_000:raise ValueError('Projekt enthält zu viele Ebenen oder Pixel.')
            layers=[]
            for record in records:
                images={}
                for key in ('image','base'):
                    if key not in record:images[key]=None;continue
                    if archive.getinfo(record[key]).file_size>300_000_000:raise ValueError('Ebenendatei zu groß.')
                    with archive.open(record[key]) as stream,Image.open(stream) as image:
                        if image.size!=size:raise ValueError('Uneinheitliche Ebenengröße.')
                        images[key]=image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
                if images['image'] is None:raise ValueError('Ebenenbild fehlt.')
                stack=tuple((str(e[0]),float(e[1]),tuple(e[2])) for e in record.get('stack',[]))
                if len({e[0] for e in stack})!=len(stack) or any(e[0] not in EFFECTS or len(e[2])!=4 for e in stack):raise ValueError('Ungültige Fotoeffekte.')
                layers.append(dict(images,name=str(record['name'])[:100],visible=bool(record['visible']),opacity=max(0,min(100,int(record['opacity']))),stack=stack))
                if 'paper_color' in record:
                    from PIL import ImageColor
                    ImageColor.getrgb(record['paper_color'])
                    layers[-1]['paper_color']=record['paper_color']
                layers[-1]['paper_opacity']=max(0,min(100,int(record.get('paper_opacity',100))))
            active=int(manifest['active'])
            if not 0<=active<len(layers):raise ValueError('Ungültige aktive Ebene.')
            return size,layers,active
