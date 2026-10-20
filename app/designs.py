"""Additional designs and decorative workspace backgrounds (never image pixels)."""
import random
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QPainter,QLinearGradient,QPixmap
from PySide6.QtWidgets import QScrollArea

# title, background, panel, button, hover, field, border, accent, selection, muted
NORMAL_DESIGNS={
    'slate':('Schieferblau','#18222e','#243242','#33465c','#455f7b','#111c28','#55718c','#a0cfff','#3b6484','#b2c5d8'),
    'cocoa':('Kakao','#261e1b','#352a25','#4b3a32','#654c40','#1d1714','#836859','#e5bb94','#72553f','#d6bfb0'),
    'plum':('Pflaume','#281c2f','#382941','#4c3759','#654971','#211627','#85648f','#deb4ee','#704f81','#d1b9d9'),
}
PLUS_DESIGNS={
    'plus_dusk':('Abendrot · Nacht','#1c121c','#2d1d2b','#432b3e','#5b394e','#160e16','#75495f','#efa7a1','#70414f','#d0afbf'),
    'plus_stars':('Sternennacht','#0c1528','#18243c','#253551','#354b6e','#090f1e','#496082','#b5d6ff','#3a587d','#acbedc'),
    'plus_aurora':('Nordlicht','#0e2026','#1b333b','#294650','#37616a','#0a191f','#487e82','#8be1c8','#376f67','#aed1ca'),
    'plus_cosmos':('Kosmos','#171126','#281e3e','#3d2e56','#554077','#100c1d','#735895','#d2b3ff','#604484','#c4b4dd'),
    'plus_moon':('Mondlicht','#1b2433','#293548','#3b4a60','#50617b','#151d2a','#7385a0','#d2e4ff','#526a8a','#c1cfe1'),
    'plus_ember':('Glut','#251419','#382026','#502e32','#6c3f3f','#1c0e12','#915655','#ffbd94','#894e43','#d9b5ab'),
    'plus_abyss':('Tiefsee','#081d28','#142e3b','#224352','#305c6a','#06161f','#40758a','#89dae7','#306b7a','#aacdd6'),
    'plus_rose':('Roséquarz','#291c2a','#3c2b3e','#533c52','#70526c','#201521','#95738b','#f0c0d7','#81566d','#ddc3d4'),
    'plus_polar':('Polarlicht','#111f32','#20344a','#304b65','#406783','#0c1727','#618da7','#a8edff','#3e748d','#b6d3e3'),
    'plus_gold':('Obsidian Gold','#1d1b20','#2c2930','#413a43','#574b55','#141217','#7c6b70','#ebcf91','#706043','#cec1b5'),
}
# Three subtle color stops; star density is intentionally low and static.
BACKDROPS={
    'plus_dusk':(('#170f19','#291928','#351d29'),False),
    'plus_stars':(('#070f20','#111c35','#1b2541'),True),
    'plus_aurora':(('#0b1929','#123936','#29253f'),False),
    'plus_cosmos':(('#100d20','#25163a','#131d36'),True),
    'plus_moon':(('#151e2c','#28344a','#344359'),True),
    'plus_ember':(('#1d1119','#351b24','#4d2926'),False),
    'plus_abyss':(('#061321','#0a2836','#103e44'),False),
    'plus_rose':(('#211524','#3a253b','#513344'),False),
    'plus_polar':(('#0a1629','#192d48','#284455'),True),
    'plus_gold':(('#111116','#25202a','#393027'),True),
}



def _palette(title,hue,saturation):
    # Consistent readable controls with individually tinted backgrounds.
    import colorsys
    def color(light,sat=saturation):
        return '#%02x%02x%02x'%tuple(round(v*255) for v in colorsys.hls_to_rgb(hue/360,light,sat))
    return (title,color(.10),color(.16),color(.23),color(.31),color(.07),color(.43),color(.78),color(.36),color(.75,.20))

for key,title,hue,sat in (
    ('olive','Olivenhain',78,.24),('copper','Kupfer',22,.37),
    ('denim','Jeansblau',215,.37),('sage','Salbei',145,.20),
    ('cherry','Kirschholz',350,.32),('petrol','Petrol',186,.42),
    ('iris','Iris',250,.38),('sand','Sandstein',40,.26),
    ('titanium','Titan',200,.16),('berry','Brombeere',315,.32)):
    NORMAL_DESIGNS[key]=_palette(title,hue,sat)

for key,title,hue,sat,stops,stars in (
    ('plus_sunset','Sonnenuntergang',18,.36,('#211827','#39202b','#50302c'),False),
    ('plus_comet','Kometenschweif',220,.42,('#10172d','#232846','#393452'),True),
    ('plus_forest','Zauberwald',150,.32,('#0d201d','#20382d','#344438'),True),
    ('plus_lagoon','Lagune',180,.40,('#091c2c','#133639','#244640'),False),
    ('plus_sakura','Sakura bei Nacht',330,.30,('#241525','#3a2536','#4d3545'),False),
    ('plus_desert','Wüstendämmerung',30,.32,('#231d27','#3c2b32','#4f3b32'),False),
    ('plus_ice','Eiskristall',200,.28,('#152536','#294050','#3d5260'),True),
    ('plus_nebula','Veilchennebel',275,.40,('#1b1231','#302344','#243854'),True),
    ('plus_firefly','Glühwürmchen',85,.28,('#171d16','#293527','#3c422d'),True),
    ('plus_ocean','Ozeannacht',230,.43,('#080f25','#19243d','#243943'),True)):
    PLUS_DESIGNS[key]=_palette(title,hue,sat)
    BACKDROPS[key]=(stops,stars)


LIGHT_PLUS={
    'plus_light_pearl':('Perlmutt','#f4f4f6','#ffffff','#e5e7ed','#d7dce6','#ffffff','#aeb7c8','#b9cdf4','#41628e','#4d5d74'),
    'plus_light_sakura':('Sakura · Hell','#fff1f5','#fffafd','#f5dfe9','#ebcbdc','#ffffff','#c9a8ba','#efb9d2','#914d72','#76566a'),
    'plus_light_glacier':('Gletscher · Hell','#eef8ff','#faffff','#dceef8','#c7e2f2','#ffffff','#a2bece','#a0d8ef','#346b88','#496777'),
    'plus_light_sage':('Salbei · Hell','#f0f7ee','#fcfffa','#e0ecdb','#cdddca','#ffffff','#a8bca1','#bddcae','#4c7042','#566b4f'),
    'plus_light_sand':('Dünensand · Hell','#fff6e9','#fffdf8','#f0e4cf','#e6d5b7','#ffffff','#c5b494','#eed39f','#80623a','#72634c'),
}
PLUS_DESIGNS.update(LIGHT_PLUS)
for key,values in LIGHT_PLUS.items():BACKDROPS[key]=((values[1],values[2],values[3]),False)

def additional_themes(tinted_style):
    result={}
    for key,values in (NORMAL_DESIGNS|PLUS_DESIGNS).items():
        title,*colors=values
        style=tinted_style(*colors)
        if key in LIGHT_PLUS:style=style.replace('#edf3fa','#243044')+'\nQPlainTextEdit,QTextEdit,QTableWidget {background:#ffffff;color:#243044;}\nQPushButton:disabled {color:#89909a;}\n'
        if key in PLUS_DESIGNS:
            a,b,c=BACKDROPS[key][0]
            style+='\nQToolBar {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 '+a+',stop:0.55 '+b+',stop:1 '+c+');}\n'
        result[key]=(title,style,colors[0])
    return result


class DesignScrollArea(QScrollArea):
    def __init__(self):
        super().__init__();self.design_colors=('#101720',)*3;self.stars=[]
        self.wallpaper=QPixmap();self.wallpaper_scaled=QPixmap();self.wallpaper_size=None;self.wallpaper_path=None;self.wallpaper_opacity=1.0

    def set_wallpaper(self,path=None,opacity=100):
        value=str(path) if path else None
        if value!=self.wallpaper_path:
            self.wallpaper_path=value;self.wallpaper=QPixmap(value) if value else QPixmap()
            self.wallpaper_scaled=QPixmap();self.wallpaper_size=None
        self.wallpaper_opacity=max(0,min(100,opacity))/100
        self.viewport().update()

    def set_design(self,key,color):
        self.design_colors,stars=BACKDROPS.get(key,((color,)*3,False))
        rng=random.Random(key)
        self.stars=[(rng.random(),rng.random(),rng.uniform(0.5,1.3),rng.randrange(80,190)) for _ in range(85)] if stars else []
        self.viewport().update()

    def paintEvent(self,event):
        p=QPainter(self.viewport())
        gradient=QLinearGradient(0,0,self.viewport().width(),self.viewport().height())
        for stop,color in zip((0,0.55,1),self.design_colors):gradient.setColorAt(stop,QColor(color))
        p.fillRect(event.rect(),gradient)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PySide6.QtCore import Qt
        p.setPen(Qt.PenStyle.NoPen)
        for x,y,radius,alpha in self.stars:
            p.setBrush(QColor(255,255,255,alpha))
            p.drawEllipse(QPointF(x*self.viewport().width(),y*self.viewport().height()),radius,radius)
        if not self.wallpaper.isNull() and self.wallpaper_opacity>0:
            size=self.viewport().size()
            if self.wallpaper_size!=size:
                self.wallpaper_scaled=self.wallpaper.scaled(size,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation);self.wallpaper_size=size
            p.setOpacity(self.wallpaper_opacity)
            p.drawPixmap((size.width()-self.wallpaper_scaled.width())//2,(size.height()-self.wallpaper_scaled.height())//2,self.wallpaper_scaled)
