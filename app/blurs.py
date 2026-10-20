"""Twenty local blur kernels; deterministic in image coordinates, no extra dependencies."""
import math
from PIL import Image, ImageFilter, ImageChops

BLUR_MODES = (
    'Vertikaler Wischblur', 'Diagonalblur rechts', 'Diagonalblur links',
    'Kreuzblur', 'Sternblur', 'Boxblur', 'Dreiecksblur', 'Linsenblur',
    'Zoomblur', 'Drehblur', 'Frostglas', 'Wellenblur', 'Wasserblur',
    'Tunnelblur', 'Doppelbild horizontal', 'Doppelbild vertikal',
    'Weicher Fokus', 'Leuchtblur', 'Schattenblur', 'Milchglas',
)


def average(images):
    result = images[0]
    for index, image in enumerate(images[1:], 2):
        result = Image.blend(result, image, 1/index)
    return result


def blur_patch(source, box, mode, strength):
    x,y,right,bottom = box
    radius = max(1, strength)
    # All sampling has an explicit halo; clamped edge samples avoid dark borders.
    halo = math.ceil(radius*4+8)
    left,top = max(0,x-halo),max(0,y-halo)
    region = source.crop((left,top,min(source.width,right+halo),min(source.height,bottom+halo)))
    # Replicate missing border pixels instead of clamping transform corners:
    # corner clamping would stretch an entire tile and create visible seams.
    padleft,padtop=max(0,halo-x),max(0,halo-y)
    padright,padbottom=max(0,right+halo-source.width),max(0,bottom+halo-source.height)
    if padleft or padtop or padright or padbottom:
        rw,rh=region.size
        expanded=Image.new('RGB',(rw+padleft+padright,rh+padtop+padbottom))
        expanded.paste(region,(padleft,padtop))
        if padleft:expanded.paste(region.crop((0,0,1,rh)).resize((padleft,rh)),(0,padtop))
        if padright:expanded.paste(region.crop((rw-1,0,rw,rh)).resize((padright,rh)),(padleft+rw,padtop))
        if padtop:expanded.paste(expanded.crop((0,padtop,expanded.width,padtop+1)).resize((expanded.width,padtop)),(0,0))
        if padbottom:expanded.paste(expanded.crop((0,padtop+rh-1,expanded.width,padtop+rh)).resize((expanded.width,padbottom)),(0,padtop+rh))
        region=expanded
        left-=padleft;top-=padtop
    local = (x-left,y-top,right-left,bottom-top)
    size = (right-x,bottom-y)
    def cut(image): return image.crop(local)
    def gauss(amount): return cut(region.filter(ImageFilter.GaussianBlur(amount)))
    def sampled(mapping):
        mesh=[]
        def point(px,py):
            sx,sy=mapping(px+x,py+y)
            return (max(0,min(region.width-1,sx-left)),max(0,min(region.height-1,sy-top)))
        # Global grid makes the same pixel independent of brush segment boundaries.
        for gy in range(y//8*8,bottom,8):
            for gx in range(x//8*8,right,8):
                ax,ay,bx,by=max(x,gx)-x,max(y,gy)-y,min(right,gx+8)-x,min(bottom,gy+8)-y
                mesh.append(((ax,ay,bx,by),point(ax,ay)+point(ax,by)+point(bx,by)+point(bx,ay)))
        return region.transform(size,Image.Transform.MESH,mesh,Image.Resampling.BILINEAR)
    def shift(dx,dy):
        # Constant offsets need only one quad, not hundreds of mesh cells.
        def point(px,py):
            return max(0,min(region.width-1,px+dx-left)),max(0,min(region.height-1,py+dy-top))
        quad=point(x,y)+point(x,bottom)+point(right,bottom)+point(right,y)
        return region.transform(size,Image.Transform.QUAD,quad,Image.Resampling.BILINEAR)
    def direction(dx,dy):
        return average([shift(dx*t*radius,dy*t*radius) for t in (-1,-.75,-.5,-.25,0,.25,.5,.75,1)])
    if mode=='Vertikaler Wischblur':return cut(region.filter(ImageFilter.BoxBlur((0,radius*3))))
    if mode=='Diagonalblur rechts':return direction(1.5,1.5)
    if mode=='Diagonalblur links':return direction(1.5,-1.5)
    if mode=='Kreuzblur':
        return Image.blend(cut(region.filter(ImageFilter.BoxBlur((radius*2,0)))),cut(region.filter(ImageFilter.BoxBlur((0,radius*2)))),.5)
    if mode=='Sternblur':return average([direction(1.5,0),direction(0,1.5),direction(1,1),direction(1,-1)])
    if mode=='Boxblur':return cut(region.filter(ImageFilter.BoxBlur(radius)))
    if mode=='Dreiecksblur':return cut(region.filter(ImageFilter.BoxBlur(radius*.65)).filter(ImageFilter.BoxBlur(radius*.65)))
    if mode=='Linsenblur':
        return average([shift(math.cos(i*math.tau/12)*radius,math.sin(i*math.tau/12)*radius) for i in range(12)]+[gauss(radius*.3)])
    if mode in ('Zoomblur','Drehblur','Tunnelblur'):
        cx,cy=source.width/2,source.height/2
        def mapping(px,py,t):
            dx,dy=px-cx,py-cy
            distance=max(1,math.hypot(dx,dy))
            if mode=='Drehblur': ox,oy=-dy/distance,dx/distance
            else: ox,oy=dx/distance,dy/distance
            return px+ox*t*radius*2,py+oy*t*radius*2
        weights=(-1,-.5,0,.5,1) if mode!='Tunnelblur' else (0,.15,.45,.9,1.6)
        return average([sampled(lambda px,py,t=t:mapping(px,py,t)) for t in weights])
    if mode in ('Frostglas','Wellenblur','Wasserblur'):
        def warp(px,py):
            if mode=='Frostglas':
                # Smooth deterministic irregular displacement, never a random flicker.
                return px+math.sin(px*.53+py*.87)*radius*.8,py+math.cos(px*.71-py*.39)*radius*.8
            if mode=='Wellenblur':return px+math.sin(py/17)*radius,py
            return px+math.sin(py/13+px/31)*radius,py+math.cos(px/19-py/29)*radius
        # Blur before displacement so distortions also suppress fine details.
        region=region.filter(ImageFilter.GaussianBlur(max(1,radius*.18)))
        return sampled(warp)
    if mode=='Doppelbild horizontal':return average([shift(-radius,0),shift(radius,0)])
    if mode=='Doppelbild vertikal':return average([shift(0,-radius),shift(0,radius)])
    if mode=='Weicher Fokus':return Image.blend(cut(region),gauss(radius),.78)
    if mode=='Leuchtblur':return ImageChops.screen(gauss(radius*.35),gauss(radius))
    if mode=='Schattenblur':return ImageChops.multiply(gauss(radius*.35),gauss(radius))
    if mode=='Milchglas':return Image.blend(gauss(radius*1.3),Image.new('RGB',size,'white'),.22)
    raise ValueError('Unbekannter Blur')
