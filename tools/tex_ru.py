"""Русские надписи на текстурах 3DS: стереть английский текст и нарисовать русский в том же стиле.

Используется из tools/tex_build.py. Все размеры - в пикселях исходной текстуры.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = '/usr/share/fonts/opentype/inter/'
FONTS = {'black': FONT_DIR + 'Inter-Black.otf', 'xbold': FONT_DIR + 'Inter-ExtraBold.otf',
         'bold': FONT_DIR + 'Inter-Bold.otf', 'semibold': FONT_DIR + 'Inter-SemiBold.otf'}
SS = 8  # сглаживание: рисуем в 8 раз крупнее и уменьшаем


def fill_columns(im, box, src_x):
    """Закрасить прямоугольник box=(x0,y0,x1,y1) копией столбца src_x (для кнопок с вертикальным градиентом)."""
    x0, y0, x1, y1 = box
    col = im.crop((src_x, y0, src_x + 1, y1))
    for x in range(x0, x1):
        im.paste(col, (x, y0))
    return im


def fill_from_columns(im, box, cols):
    """Закрасить box построчно средним цветом столбцов cols (участки фона без текста)."""
    x0, y0, x1, y1 = box
    px = im.load()
    for y in range(y0, y1):
        c = [px[x, y] for x in cols]
        avg = tuple(sum(p[k] for p in c) // len(c) for k in range(4))
        for x in range(x0, x1):
            px[x, y] = avg
    return im


def fill_rows(im, box, src_y):
    x0, y0, x1, y1 = box
    row = im.crop((x0, src_y, x1, src_y + 1))
    for y in range(y0, y1):
        im.paste(row, (x0, y))
    return im


def text_layer(size, box, text, color=(255, 255, 255, 255), stroke=(20, 40, 40, 255), stroke_w=1.0,
               font='black', height=None, align='center', max_squeeze=0.55, valign='center'):
    """Слой RGBA размера size с текстом, вписанным в box. height - высота заглавных букв в пикселях.
    Если текст не помещается по ширине, он сжимается по горизонтали (не уже max_squeeze)."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    cap = height or bh * 0.8
    f = ImageFont.truetype(FONTS[font], int(cap * SS / 0.73))  # у Inter высота заглавных ~0.73 em
    sw = max(0, round(stroke_w * SS))
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    tw, th = r - l, b - t
    big = Image.new('RGBA', (tw + 2, th + 2), (0, 0, 0, 0))
    ImageDraw.Draw(big).text((-l + 1, -t + 1), text, font=f, fill=color, stroke_width=sw, stroke_fill=stroke)
    # уменьшаем: по высоте до нужного размера, по ширине - сколько влезет
    th_px = (th + 2) / SS
    tw_px = (tw + 2) / SS
    sx = 1.0
    if tw_px > bw:
        sx = max(max_squeeze, bw / tw_px)
    nw, nh = max(1, round(tw_px * sx)), max(1, round(th_px))
    small = big.resize((nw, nh), Image.LANCZOS)
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    if align == 'center': px = x0 + (bw - nw) // 2
    elif align == 'left': px = x0
    else: px = x1 - nw
    py = y0 + (bh - nh) // 2 if valign == 'center' else y0
    layer.alpha_composite(small, (px, py))
    return layer


def draw_text(im, box, text, **kw):
    im.alpha_composite(text_layer(im.size, box, text, **kw))
    return im


def interp_vertical(im, box):
    """Стереть содержимое box, протянув цвета между строкой над ним и строкой под ним (для неоднородного фона)."""
    x0, y0, x1, y1 = box
    px = im.load()
    for x in range(x0, x1):
        a, b = px[x, y0 - 1], px[x, y1]
        for y in range(y0, y1):
            t = (y - y0 + 1) / (y1 - y0 + 1)
            px[x, y] = tuple(round(a[k] * (1 - t) + b[k] * t) for k in range(4))
    return im


def right_edge(im, y, thr=128):
    """Последний непрозрачный пиксель строки y."""
    px = im.load()
    for x in range(im.width - 1, -1, -1):
        if px[x, y][3] >= thr: return x
    return -1


def clear(im):
    im.paste((0, 0, 0, 0), (0, 0, im.width, im.height))
    return im


def erase_text_by_column(im, box, is_text):
    """Стереть надпись на неоднородном фоне: в каждом столбце box пиксели надписи (is_text(r,g,b,a))
    заменяются средним цветом остальных (фоновых) пикселей того же столбца."""
    x0, y0, x1, y1 = box
    px = im.load()
    for x in range(x0, x1):
        bg = [px[x, y] for y in range(y0, y1) if px[x, y][3] > 200 and not is_text(*px[x, y])]
        if not bg:
            continue
        avg = tuple(sum(p[k] for p in bg) // len(bg) for k in range(4))
        for y in range(y0, y1):
            if px[x, y][3] > 200 and is_text(*px[x, y]):
                px[x, y] = avg
    return im


def erase_text_by_row(im, box, is_text):
    """Как erase_text_by_column, но среднее берётся по строке (фон меняется поперёк надписи)."""
    x0, y0, x1, y1 = box
    px = im.load()
    for y in range(y0, y1):
        bg = [px[x, y] for x in range(x0, x1) if px[x, y][3] > 200 and not is_text(*px[x, y])]
        if not bg:
            continue
        avg = tuple(sum(p[k] for p in bg) // len(bg) for k in range(4))
        for x in range(x0, x1):
            if px[x, y][3] > 200 and is_text(*px[x, y]):
                px[x, y] = avg
    return im


def rbox(box, w):
    """Прямоугольник из координат исходной текстуры шириной w в координаты после поворота на 90° против часовой."""
    x0, y0, x1, y1 = box
    return (y0, w - x1, y1, w - x0)


def rbox_cw(box, h):
    """Прямоугольник из исходной текстуры высотой h в координаты после поворота на 90° по часовой."""
    x0, y0, x1, y1 = box
    return (h - y1, x0, h - y0, x1)


def inpaint(im, mask, iters=60):
    """Залить пиксели mask (множество (x,y)) цветами соседей: простое «размывание» фона внутрь дыры."""
    import numpy as np
    a = np.asarray(im, dtype=float).copy()
    m = np.zeros(a.shape[:2], bool)
    for x, y in mask:
        m[y, x] = True
    known = ~m
    for _ in range(iters):
        acc = np.zeros_like(a); cnt = np.zeros(a.shape[:2])
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.roll(np.roll(a, dy, 0), dx, 1); kn = np.roll(np.roll(known, dy, 0), dx, 1)
            acc += sh * kn[..., None]; cnt += kn
        fill = m & (cnt > 0)
        a[fill] = acc[fill] / cnt[fill][:, None]
        known = known | fill
    im.paste(Image.fromarray(a.round().clip(0, 255).astype('uint8'), 'RGBA'))
    return im


def text_mask(im, box, is_text, grow=1):
    x0, y0, x1, y1 = box
    px = im.load()
    pts = {(x, y) for x in range(x0, x1) for y in range(y0, y1) if is_text(*px[x, y])}
    for _ in range(grow):
        pts |= {(x + dx, y + dy) for x, y in pts for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if x0 <= x + dx < x1 and y0 <= y + dy < y1}
    return pts


def draw_arc_text(im, center, radius, text, height, color, stroke, stroke_w=1.2, font='black', spread=1.0):
    """Текст по дуге окружности (центр ниже текста): буквы ставятся по верхней дуге, середина - над центром."""
    import math
    f = ImageFont.truetype(FONTS[font], int(height * SS / 0.73))
    sw = max(0, round(stroke_w * SS))
    widths = [f.getbbox(ch, stroke_width=sw)[2] - f.getbbox(ch, stroke_width=sw)[0] for ch in text]
    total = sum(widths) / SS * spread
    ang = -total / radius / 2
    cx, cy = center
    for ch, w in zip(text, widths):
        w_px = w / SS * spread
        a = ang + w_px / radius / 2
        l, t, r, b = f.getbbox(ch, stroke_width=sw)
        big = Image.new('RGBA', (r - l + 2, b - t + 2), (0, 0, 0, 0))
        ImageDraw.Draw(big).text((-l + 1, -t + 1), ch, font=f, fill=color, stroke_width=sw, stroke_fill=stroke)
        small = big.resize((max(1, round((r - l + 2) / SS)), max(1, round((b - t + 2) / SS))), Image.LANCZOS)
        small = small.rotate(-math.degrees(a), resample=Image.BICUBIC, expand=True)
        px_ = cx + radius * math.sin(a); py_ = cy - radius * math.cos(a)
        im.alpha_composite(small, (round(px_ - small.width / 2), round(py_ - small.height / 2)))
        ang += w_px / radius
    return im


def draw_smile_text(im, center, radius, a0, a1, text, height, color, stroke, stroke_w=1.2, font='black', max_gap=1.5):
    """Текст по нижней дуге окружности (центр выше текста, дуга «улыбкой»).
    Низ букв лежит на окружности радиуса radius; буквы равномерно распределены между углами a0..a1
    (в градусах от направления вниз, плюс - вправо и вверх)."""
    import math
    f = ImageFont.truetype(FONTS[font], int(height * SS / 0.73))
    sw = max(0, round(stroke_w * SS))
    glyphs = []
    for ch in text:
        l, t, r, b = f.getbbox(ch, stroke_width=sw)
        big = Image.new('RGBA', (r - l + 2, b - t + 2), (0, 0, 0, 0))
        ImageDraw.Draw(big).text((-l + 1, -t + 1), ch, font=f, fill=color, stroke_width=sw, stroke_fill=stroke)
        glyphs.append(big.resize((max(1, round((r - l + 2) / SS)), max(1, round((b - t + 2) / SS))), Image.LANCZOS))
    rc = radius - height / 2                       # центры букв чуть ближе к центру окружности
    widths = [g.width for g in glyphs]
    span = math.radians(a1 - a0)
    gap = (span * rc - sum(widths)) / max(1, len(glyphs) - 1)
    gap = min(max(gap, 0.0), max_gap)
    total = sum(widths) + gap * (len(glyphs) - 1)
    ang = math.radians((a0 + a1) / 2) - total / rc / 2
    cx, cy = center
    for g, w in zip(glyphs, widths):
        a = ang + w / rc / 2
        rg = g.rotate(math.degrees(a), resample=Image.BICUBIC, expand=True)
        px_ = cx + rc * math.sin(a); py_ = cy + rc * math.cos(a)
        im.alpha_composite(rg, (round(px_ - rg.width / 2), round(py_ - rg.height / 2)))
        ang += (w + gap) / rc
    return im


def outlined_text_mask(im, box, is_fill, is_outline, reach=2):
    """Маска надписи «светлая заливка + тёмная обводка»: берём пиксели заливки и только те тёмные пиксели,
    что лежат не дальше reach от заливки (чтобы не задеть контуры рисунка вокруг)."""
    x0, y0, x1, y1 = box
    px = im.load()
    fill = {(x, y) for x in range(x0, x1) for y in range(y0, y1) if is_fill(*px[x, y])}
    near = set(fill)
    for _ in range(reach):
        near |= {(x + dx, y + dy) for x, y in near for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if x0 <= x + dx < x1 and y0 <= y + dy < y1}
    m = fill | {(x, y) for x, y in near if is_outline(*px[x, y])}
    # плюс один пиксель сглаживания вокруг
    return m | {(x + dx, y + dy) for x, y in m for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if x0 <= x + dx < x1 and y0 <= y + dy < y1 and (x + dx, y + dy) in near}
