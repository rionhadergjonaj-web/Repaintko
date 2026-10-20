"""Exact four-connected scanline fill; pixel comparisons run in Pillow's C core."""
import re
from bisect import bisect_left
from PIL import Image, ImageChops, ImageDraw


def filled_image(source, point, color):
    x, y = point
    target = source.getpixel(point)
    if target == color:
        return source
    difference = ImageChops.difference(source, Image.new(source.mode, source.size, target))
    channels = difference.split()
    difference = channels[0]
    for channel in channels[1:]:
        difference = ImageChops.lighter(difference, channel)
    matches = difference.point([255] + [0] * 255)
    del channels, difference
    mask = Image.new('L', source.size)
    pen = ImageDraw.Draw(mask)
    rows, seen = {}, set()
    pattern = re.compile(b'\xff+')

    def spans(row, left, right):
        if not 0 <= row < source.height:
            return []
        if row not in rows:
            runs = [(m.start(), m.end()-1) for m in pattern.finditer(matches.crop((0,row,source.width,row+1)).tobytes())]
            rows[row] = runs, [end for _, end in runs]
        runs, ends = rows[row]
        result = []
        for start, end in runs[bisect_left(ends, left):]:
            if start > right:
                break
            key = (row, start, end)
            if key not in seen:
                seen.add(key)
                result.append(key)
        return result

    pending = spans(y, x, x)
    while pending:
        row, left, right = pending.pop()
        pen.line((left,row,right,row), fill=255)
        pending.extend(spans(row-1,left,right))
        pending.extend(spans(row+1,left,right))
    result = source.copy()
    result.paste(color, (0,0,*source.size), mask)
    return result
