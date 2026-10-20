"""Round, continuous redaction strokes sampled from an immutable stroke source."""
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageStat
from collections import OrderedDict
from blurs import BLUR_MODES, blur_patch

CENSOR_MODES = ('Verpixeln', 'Mosaik', 'Weichzeichnen', 'Spirale', 'Speed-Streifen',
                'Feine Wischstreifen', 'Malpinsel-Blur') + BLUR_MODES


def paint_patch(source, box, strength):
    """Deterministic, globally aligned paint daubs, sampled from the stroke source."""
    x1,y1,x2,y2=box
    cell=max(4,round(strength*0.8))
    # Rasterize whole daubs before cropping; clipping a polygon changes edge rounding.
    x1,y1,x2,y2=x1-cell*3,y1-cell*3,x2+cell*3,y2+cell*3
    pad=math.ceil(max(1,strength/5)*4)
    ext=(max(0,x1-pad),max(0,y1-pad),min(source.width,x2+pad),min(source.height,y2+pad))
    patch=source.crop(ext).filter(ImageFilter.GaussianBlur(max(1,strength/5))).crop(
        (x1-ext[0],y1-ext[1],x2-ext[0],y2-ext[1]))
    pen=ImageDraw.Draw(patch)
    for gy in range(y1//cell-2,math.ceil(y2/cell)+2):
        for gx in range(x1//cell-2,math.ceil(x2/cell)+2):
            rng=random.Random(gx*92837111+gy*689287499)
            cx=gx*cell+rng.uniform(-0.3,0.3)*cell
            cy=gy*cell+rng.uniform(-0.3,0.3)*cell
            sample=(max(0,int(cx-cell/2)),max(0,int(cy-cell/2)),
                    min(source.width,int(cx+cell/2)+1),min(source.height,int(cy+cell/2)+1))
            if sample[2]<=sample[0] or sample[3]<=sample[1]:continue
            color=tuple(round(v) for v in ImageStat.Stat(source.crop(sample)).mean)
            points=[]
            for n in range(10):
                angle=n*math.tau/10
                radius=cell*rng.uniform(0.7,1.05)
                dx,dy=math.cos(angle)*radius,math.sin(angle)*radius*0.6
                points.append((round(cx+dx-dy*0.6)-x1,round(cy+dy-dx*0.6)-y1))
            pen.polygon(points,fill=color)
    return patch.crop((box[0]-x1,box[1]-y1,box[2]-x1,box[3]-y1))


def spiral_patch(source, box, center, radius, strength):
    x1, y1, x2, y2 = box
    def mapped(x, y):
        dx, dy = x+x1-center[0], y+y1-center[1]
        r = math.hypot(dx, dy)
        t = max(0, 1-r/max(1, radius))
        angle = math.atan2(dy, dx)+(strength/80)*math.tau*t*t
        r *= 1+0.9*t
        return (max(0, min(source.width-1, center[0]+math.cos(angle)*r)),
                max(0, min(source.height-1, center[1]+math.sin(angle)*r)))
    mesh = []
    for y in range(0, y2-y1, 8):
        for x in range(0, x2-x1, 8):
            right, bottom = min(x+8, x2-x1), min(y+8, y2-y1)
            mesh.append(((x, y, right, bottom), mapped(x, y)+mapped(x, bottom)+mapped(right, bottom)+mapped(right, y)))
    return source.transform((x2-x1, y2-y1), Image.Transform.MESH, mesh, Image.Resampling.BILINEAR)


def filter_patch(source, box, point, radius, mode, strength):
    x1,y1,x2,y2 = box
    size = (x2-x1,y2-y1)
    if mode in BLUR_MODES:
        filtered = blur_patch(source,box,mode,strength)
    elif mode == 'Feine Wischstreifen':
        length=strength*4
        ext=(max(0,x1-length),y1,min(source.width,x2+length),y2)
        blurred=source.crop(ext).filter(ImageFilter.BoxBlur((length,0)))
        filtered=blurred.crop((x1-ext[0],0,x2-ext[0],size[1]))
    elif mode == 'Malpinsel-Blur':
        filtered=paint_patch(source,box,strength)
    elif mode == 'Spirale':
        filtered = spiral_patch(source, box, point, radius, strength)
    elif mode == 'Speed-Streifen':
        pad = strength*3
        ext = (max(0, x1-pad), y1, min(source.width, x2+pad), y2)
        region = source.crop(ext)
        bands = max(1, region.height//max(2, strength//3))
        small = region.resize((max(1, region.width//max(4, strength*3)), bands), Image.Resampling.BOX)
        streaks = small.resize(region.size, Image.Resampling.NEAREST)
        filtered = streaks.crop((x1-ext[0], 0, x2-ext[0], size[1]))
    elif mode == 'Weichzeichnen':
        pad = strength*4
        ext = (max(0, x1-pad), max(0, y1-pad), min(source.width, x2+pad), min(source.height, y2+pad))
        blurred = source.crop(ext).filter(ImageFilter.GaussianBlur(strength))
        filtered = blurred.crop((x1-ext[0], y1-ext[1], x2-ext[0], y2-ext[1]))
    elif mode in ('Verpixeln', 'Mosaik'):
        filtered = Image.new('RGB', size)
        draw = ImageDraw.Draw(filtered)
        # Global block alignment prevents seams or repeated pixelation on overlaps.
        for y in range(y1//strength*strength, y2, strength):
            for x in range(x1//strength*strength, x2, strength):
                cell = source.crop((x, y, min(source.width, x+strength), min(source.height, y+strength)))
                color = tuple(round(v) for v in ImageStat.Stat(cell).mean)
                draw.rectangle((x-x1, y-y1, x+strength-x1-1, y+strength-y1-1), fill=color)
                if mode == 'Mosaik' and min(cell.size) > 1:
                    triangle = Image.new('L', cell.size)
                    ImageDraw.Draw(triangle).polygon([(0, 0), (cell.width-1, 0), (0, cell.height-1)], fill=255)
                    tint = tuple(round(v) for v in ImageStat.Stat(cell, triangle).mean)
                    draw.polygon([(x-x1, y-y1), (x-x1+cell.width-1, y-y1),
                                  (x-x1, y-y1+cell.height-1)], fill=tint)
    else:
        raise ValueError('Unbekannter Zensurmodus')
    return filtered


class StrokeCache:
    """Bounded tile cache tied to one immutable source and one brush stroke."""
    def __init__(self):
        self.tiles = OrderedDict()
        self.source = None
        self.hits = self.misses = 0

    def patch(self, source, box, mode, strength):
        if self.source is not source:
            self.tiles.clear()
            self.source = source
        x,y,right,bottom = box
        output = Image.new('RGB',(right-x,bottom-y))
        for top in range(y//128*128,bottom,128):
            for left in range(x//128*128,right,128):
                key = (left,top,mode,strength)
                if key not in self.tiles:
                    tilebox=(left,top,min(source.width,left+128),min(source.height,top+128))
                    self.tiles[key]=filter_patch(source,tilebox,(0,0),0,mode,strength)
                    self.misses += 1
                    if len(self.tiles)>128:self.tiles.popitem(last=False)
                else:self.hits += 1
                self.tiles.move_to_end(key)
                output.paste(self.tiles[key],(left-x,top-y))
        return output


def censor_segment(destination, source, a, b, diameter, mode, strength, cache=None):
    diameter = max(8, min(400, int(diameter)))
    strength = max(2, min(80, int(strength)))
    distance = math.hypot(b[0]-a[0], b[1]-a[1])
    steps = max(1, math.ceil(distance/max(8, diameter/2 if mode=='Spirale' else diameter*2)))
    radius = diameter/2
    bounds = [destination.width, destination.height, 0, 0]
    previous = a
    for n in range(1, steps+1):
        point = (a[0]+(b[0]-a[0])*n/steps, a[1]+(b[1]-a[1])*n/steps)
        x1 = max(0, math.floor(min(previous[0], point[0])-radius-1))
        y1 = max(0, math.floor(min(previous[1], point[1])-radius-1))
        x2 = min(source.width, math.ceil(max(previous[0], point[0])+radius+2))
        y2 = min(source.height, math.ceil(max(previous[1], point[1])+radius+2))
        if x2 <= x1 or y2 <= y1:
            previous = point
            continue
        box = (x1, y1, x2, y2)
        size = (x2-x1, y2-y1)
        if cache is not None and mode not in ('Spirale', 'Speed-Streifen'):
            filtered = cache.patch(source,box,mode,strength)
        else:
            filtered = filter_patch(source,box,point,radius,mode,strength)
        mask = Image.new('L', size)
        pen = ImageDraw.Draw(mask)
        local = [(previous[0]-x1, previous[1]-y1), (point[0]-x1, point[1]-y1)]
        pen.line(local, fill=255, width=diameter)
        for x, y in local:
            pen.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
        destination.paste(filtered, (x1, y1), mask)
        bounds = [min(bounds[0], x1), min(bounds[1], y1), max(bounds[2], x2), max(bounds[3], y2)]
        previous = point
    return tuple(bounds)
