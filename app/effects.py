"""Non-destructive RGB filter functions; no GUI calls, safe for worker threads."""
from dataclasses import dataclass
import math
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True)
class Effect:
    title: str
    group: str
    description: str
    minimum: int = 0
    maximum: int = 100
    default: int = 50
    unit: str = '%'


EFFECTS = {
    'pixelate': Effect('Verpixeln', 'Zensur', 'Vergröbert Details in quadratische Blöcke.', 2, 160, 24, 'px'),
    'blur': Effect('Weichzeichnen', 'Zensur', 'Verwischt Details mit einem Gauß-Weichzeichner.', 1, 80, 12, 'px'),
    'brightness': Effect('Helligkeit', 'Korrekturen', 'Hellt das Bild auf oder dunkelt es ab.', -100, 100, 15),
    'contrast': Effect('Kontrast', 'Korrekturen', 'Verstärkt oder reduziert den Unterschied zwischen hell und dunkel.', -100, 100, 25),
    'saturation': Effect('Sättigung', 'Korrekturen', 'Von entsättigten Farben bis zu kräftigen Farbtönen.', -100, 100, 25),
    'sharpness': Effect('Schärfen', 'Korrekturen', 'Betont feine Kanten und Details.', 0, 200, 80),
    'dust': Effect('Staub entfernen', 'Korrekturen', 'Reduziert kleine helle und dunkle Flecken mit einem selektiven Medianfilter.', 0, 100, 65),
    'clarity': Effect('Klarheit', 'Korrekturen', 'Verstärkt lokale Kontraste auf größeren Strukturen.', 0, 100, 35),
    'structure': Effect('Struktur', 'Korrekturen', 'Betont feine Texturen und Oberflächendetails.', 0, 100, 40),
    'autocontrast': Effect('Auto-Kontrast', 'Korrekturen', 'Spreizt den vorhandenen Tonwertumfang.', 0, 100, 100),
    'grayscale': Effect('Schwarzweiß', 'Looks', 'Mischt eine Schwarzweiß-Umsetzung in das Bild.', 0, 100, 100),
    'sepia': Effect('Sepia', 'Looks', 'Warme Brauntöne für einen klassischen Fotolook.', 0, 100, 85),
    'warm': Effect('Warmer Look', 'Looks', 'Wärmere Rot- und Gelbtöne.', 0, 100, 40),
    'cool': Effect('Kühler Look', 'Looks', 'Kühle Blautöne für eine ruhigere Stimmung.', 0, 100, 40),
    'vignette': Effect('Vignette', 'Looks', 'Dunkelt die Ränder weich ab.', 0, 100, 55),
    'glow': Effect('Weiches Leuchten', 'Looks', 'Mischt weiches Licht in helle Bildbereiche.', 0, 100, 40),
    'posterize': Effect('Poster / Comic', 'Grafik', 'Reduziert die Anzahl der Farbstufen.', 1, 8, 3, 'Bit'),
    'threshold': Effect('Schablone', 'Grafik', 'Wandelt das Bild in reines Schwarz und Weiß um.', 0, 255, 128, ''),
    'edges': Effect('Leuchtende Kanten', 'Grafik', 'Hebt Konturen vor einem dunklen Hintergrund hervor.', 0, 100, 100),
    'emboss': Effect('Relief', 'Grafik', 'Erzeugt eine geprägte Oberfläche.', 0, 100, 100),
    'invert': Effect('Negativ', 'Grafik', 'Kehrt die Farben um.', 0, 100, 100),
}


def apply_effect(source, key, value=None, scale=1.0):
    """Return a fresh image. scale adjusts spatial filters for thumbnail previews."""
    spec = EFFECTS[key]
    value = spec.default if value is None else float(value)
    if not math.isfinite(value) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Ungültige Effektstärke oder Vorschaugröße.')
    value = max(spec.minimum, min(spec.maximum, value))
    image = source if source.mode == 'RGB' else source.convert('RGB')
    if key in ('dust', 'clarity', 'structure'):
        if value == 0:
            return image.copy()
        if key == 'dust':
            median = image.filter(ImageFilter.MedianFilter(3))
            channels = ImageChops.difference(image, median).split()
            difference = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            threshold = round(60 - value*0.5)
            mask = difference.point([255 if p >= threshold else 0 for p in range(256)])
            cleaned = Image.composite(median, image, mask)
            return Image.blend(image, cleaned, value/100)
        # Separate spatial scales: clarity for broad local contrast, structure for texture.
        radius = (18 if key == 'clarity' else 2.5)*scale
        return image.filter(ImageFilter.UnsharpMask(radius=max(0.2, radius),
                            percent=round(value*1.5), threshold=3 if key == 'clarity' else 1))
    if key == 'pixelate':
        block = max(1, round(value*scale))
        small = (max(1, math.ceil(image.width/block)), max(1, math.ceil(image.height/block)))
        return image.resize(small, Image.Resampling.BOX).resize(image.size, Image.Resampling.NEAREST)
    if key == 'blur':
        return image.filter(ImageFilter.GaussianBlur(max(0.1, value*scale)))
    if key in ('brightness', 'contrast', 'saturation'):
        enhancer = {'brightness': ImageEnhance.Brightness, 'contrast': ImageEnhance.Contrast,
                    'saturation': ImageEnhance.Color}[key]
        return enhancer(image).enhance(1+value/100)
    if key == 'sharpness':
        return image.filter(ImageFilter.UnsharpMask(radius=max(0.2, 2*scale), percent=round(value), threshold=3))
    if key == 'posterize':
        return ImageOps.posterize(image, round(value))
    if key == 'threshold':
        return ImageOps.grayscale(image).point(lambda p: 255 if p >= value else 0).convert('RGB')
    if key == 'autocontrast':
        filtered = ImageOps.autocontrast(image)
    elif key == 'grayscale':
        filtered = ImageOps.grayscale(image).convert('RGB')
    elif key == 'sepia':
        filtered = ImageOps.colorize(ImageOps.grayscale(image), '#26170d', '#fff0c2')
    elif key in ('warm', 'cool'):
        shifts = (22, 6, -18) if key == 'warm' else (-15, 4, 24)
        filtered = Image.merge('RGB', tuple(channel.point([max(0, min(255, p+shift)) for p in range(256)])
                                            for channel, shift in zip(image.split(), shifts)))
    elif key == 'vignette':
        # Small reusable-resolution mask, not a Python loop over the full photo.
        size = 128
        mask = Image.new('L', (size, size))
        mask.putdata([round(255*min(1, ((x/(size-1)*2-1)**2+(y/(size-1)*2-1)**2)/2))
                      for y in range(size) for x in range(size)])
        mask = mask.resize(image.size, Image.Resampling.BILINEAR)
        filtered = Image.composite(Image.new('RGB', image.size, 'black'), image, mask)
    elif key == 'glow':
        soft = image.filter(ImageFilter.GaussianBlur(max(0.2, 10*scale)))
        filtered = ImageChops.screen(image, soft)
    elif key == 'edges':
        filtered = image.filter(ImageFilter.FIND_EDGES)
    elif key == 'emboss':
        filtered = image.filter(ImageFilter.EMBOSS)
    elif key == 'invert':
        filtered = ImageOps.invert(image)
    else:
        raise ValueError('Unbekannter Effekt')
    return Image.blend(image, filtered, value/100)


def update_effect_stack(stack, key, value, box):
    """One entry per effect type, preserving its original position in the chain."""
    replacement = (key, float(value), tuple(box))
    result = []
    replaced = False
    for entry in stack:
        if entry[0] == key:
            if not replaced:
                result.append(replacement)
                replaced = True
        else:
            result.append(entry)
    if not replaced:
        result.append(replacement)
    return tuple(result)


def render_effect_stack(base, stack, scale=1.0, origin=(0, 0)):
    result = base.copy()
    for key, value, box in stack:
        x1 = max(0, round((box[0]-origin[0])*scale))
        y1 = max(0, round((box[1]-origin[1])*scale))
        x2 = min(result.width, round((box[2]-origin[0])*scale))
        y2 = min(result.height, round((box[3]-origin[1])*scale))
        if x2 > x1 and y2 > y1:
            region = (x1, y1, x2, y2)
            result.paste(apply_effect(result.crop(region), key, value, scale), (x1, y1))
    return result


def render_effect_edit(payload, key, value, scale):
    base, stack, box, origin = payload
    return render_effect_stack(base, update_effect_stack(stack, key, value, box), scale, origin)
