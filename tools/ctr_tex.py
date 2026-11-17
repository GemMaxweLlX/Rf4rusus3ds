"""Текстуры 3DS в контейнере CGFX (.bctex, .bcmdl): чтение и замена картинок.

  python3 tools/ctr_tex.py dump FILE OUTDIR        - сохранить все текстуры файла в PNG
  python3 tools/ctr_tex.py list FILE               - список текстур (имя, размер, формат)
  python3 tools/ctr_tex.py put FILE NAME PNG [OUT] - заменить текстуру NAME картинкой PNG того же размера

Поддерживаются форматы ETC1, ETC1A4, RGBA8, RGB8, RGBA5551, RGB565, RGBA4, LA8, L8, A8, LA4, L4, A4.
Кодирование ETC1 своё (без внешних библиотек): перебор режимов блока, достаточно для надписей интерфейса.
"""
import struct, sys, os
from PIL import Image

FMT = {0: 'RGBA8', 1: 'RGB8', 2: 'RGBA5551', 3: 'RGB565', 4: 'RGBA4', 5: 'LA8', 6: 'HILO8', 7: 'L8',
       8: 'A8', 9: 'LA4', 10: 'L4', 11: 'A4', 12: 'ETC1', 13: 'ETC1A4'}
BPP = {'RGBA8': 32, 'RGB8': 24, 'RGBA5551': 16, 'RGB565': 16, 'RGBA4': 16, 'LA8': 16, 'HILO8': 16, 'L8': 8,
       'A8': 8, 'LA4': 8, 'L4': 4, 'A4': 4, 'ETC1': 4, 'ETC1A4': 8}
ETC_TAB = [(2, 8), (5, 17), (9, 29), (13, 42), (18, 60), (24, 80), (33, 106), (47, 183)]


def u32(b, o): return struct.unpack_from('<I', b, o)[0]


def textures(b):
    """Найти все TXOB с картинкой: (имя, ширина, высота, формат, смещение данных, длина)."""
    out, i = [], 0
    while True:
        m = b.find(b'TXOB', i)
        if m < 0: break
        i = m + 4
        try:
            if u32(b, m - 4) & 0xFF != 0x11: continue
            name_o = m + 0x08 + u32(b, m + 0x08)
            name = b[name_o:b.index(b'\0', name_o)].decode('ascii', 'replace')
            h, w, f = u32(b, m + 0x14), u32(b, m + 0x18), u32(b, m + 0x30)
            img = m + 0x34 + u32(b, m + 0x34)
            ih, iw, size = u32(b, img), u32(b, img + 4), u32(b, img + 8)
            data = img + 0x0C + u32(b, img + 0x0C)
            if f not in FMT or (ih, iw) != (h, w) or data + size > len(b): continue
            if size < w * h * BPP[FMT[f]] // 8: continue
            out.append((name, w, h, FMT[f], data, w * h * BPP[FMT[f]] // 8))
        except (struct.error, ValueError):
            continue
    return out


# ---------- порядок пикселей 3DS: плитки 8x8, внутри - Z-порядок
def _morton(i):
    x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
    y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
    return x, y
MORTON = [_morton(i) for i in range(64)]


def _clamp(v): return 0 if v < 0 else 255 if v > 255 else v


def etc1_decode_block(v):
    """v - 64-битный блок ETC1 (как в стандарте). Возвращает 16 цветов [(r,g,b)] по индексу x*4+y."""
    hi = v >> 32
    diff, flip = (hi >> 1) & 1, hi & 1
    t1, t2 = (hi >> 5) & 7, (hi >> 2) & 7
    if diff:
        def c5(a, d):
            d = d - 8 if d & 4 else d
            return a, a + d
        r1, r2 = c5((hi >> 27) & 31, (hi >> 24) & 7)
        g1, g2 = c5((hi >> 19) & 31, (hi >> 16) & 7)
        b1, b2 = c5((hi >> 11) & 31, (hi >> 8) & 7)
        ex = lambda c: (c << 3) | (c >> 2)
        c1 = (ex(r1), ex(g1), ex(b1)); c2 = (ex(r2 & 31), ex(g2 & 31), ex(b2 & 31))
    else:
        ex = lambda c: c * 17
        c1 = (ex((hi >> 28) & 15), ex((hi >> 20) & 15), ex((hi >> 12) & 15))
        c2 = (ex((hi >> 24) & 15), ex((hi >> 16) & 15), ex((hi >> 8) & 15))
    lo = v & 0xFFFFFFFF
    res = [None] * 16
    for x in range(4):
        for y in range(4):
            k = x * 4 + y
            sub = (y >= 2) if flip else (x >= 2)
            c, t = (c2, ETC_TAB[t2]) if sub else (c1, ETC_TAB[t1])
            idx = (((lo >> (16 + k)) & 1) << 1) | ((lo >> k) & 1)
            mod = (t[0], t[1], -t[0], -t[1])[idx]
            res[k] = tuple(_clamp(ch + mod) for ch in c)
    return res


import numpy as np
_TAB = np.array([[a, b, -a, -b] for a, b in ETC_TAB])            # (8,4)
_R = 4
_OFF = np.array([(i, j, k) for i in range(-_R, _R + 1) for j in range(-_R, _R + 1) for k in range(-_R, _R + 1)])


def _sub_idx(flip, sub):
    return [k for k in range(16) if ((k & 3) >= 2 if flip else (k >> 2) >= 2) == bool(sub)]


def _sub_errors(P, q, bits):
    """P (8,3) пиксели подблока; q (N,3) кандидаты базового цвета в bits битах.
    Возвращает ошибки (N,) , лучшие таблицы (N,) и индексы модификаторов (N,8)."""
    base = (q << 3) | (q >> 2) if bits == 5 else q * 17
    vals = np.clip(base[:, None, None, :] + _TAB[None, :, :, None], 0, 255)          # (N,8,4,3)
    err = ((vals[:, :, :, None, :] - P[None, None, None, :, :]) ** 2).sum(-1)         # (N,8,4,8)
    idx = err.argmin(2)                                                              # (N,8,8)
    e = err.min(2).sum(-1)                                                           # (N,8)
    t = e.argmin(1)
    n = np.arange(len(q))
    return e[n, t], t, idx[n, t]


def _cands(avg, bits, P=None):
    """Кандидаты базового цвета: вокруг среднего и вокруг середины между самым тёмным и самым светлым
    пикселем подблока (так лучше передаются контрастные края букв)."""
    mx = (1 << bits) - 1
    centers = [avg]
    if P is not None:
        l = P.sum(1); centers.append((P[l.argmin()] + P[l.argmax()]) / 2)
    qs = []
    for c in centers:
        q0 = np.clip(np.round(np.asarray(c) * mx / 255).astype(int), 0, mx)
        qs.append(np.clip(q0[None, :] + _OFF, 0, mx))
    return np.unique(np.concatenate(qs), axis=0)


def etc1_encode_block(px):
    """px - 16 цветов (r,g,b) по индексу x*4+y. Перебор базовых цветов вокруг среднего, обоих режимов и разбиений."""
    A = np.array(px, dtype=int)
    best = None
    for flip in (0, 1):
        subs = [_sub_idx(flip, s) for s in (0, 1)]
        Ps = [A[ks] for ks in subs]
        # индивидуальный режим: подблоки независимы
        r = []
        for P in Ps:
            q = _cands(P.mean(0), 4, P); e, t, idx = _sub_errors(P, q, 4); i = e.argmin()
            r.append((e[i], q[i], t[i], idx[i]))
        err = r[0][0] + r[1][0]
        if best is None or err < best[0]:
            best = (err, flip, 0, r, subs)
        # разностный режим: 5 бит, разность второго цвета -4..3
        q0 = _cands(Ps[0].mean(0), 5, Ps[0]); q1 = _cands(Ps[1].mean(0), 5, Ps[1])
        e0, t0, i0 = _sub_errors(Ps[0], q0, 5); e1, t1, i1 = _sub_errors(Ps[1], q1, 5)
        d = q1[None, :, :] - q0[:, None, :]
        ok = ((d >= -4) & (d <= 3)).all(-1)
        if ok.any():
            tot = np.where(ok, e0[:, None] + e1[None, :], np.inf)
            a, b = np.unravel_index(tot.argmin(), tot.shape)
            if tot[a, b] < best[0]:
                best = (tot[a, b], flip, 1, [(e0[a], q0[a], t0[a], i0[a]), (e1[b], q1[b], t1[b], i1[b])], subs)
    err, flip, diff, r, subs = best
    (_, qa, ta, ia), (_, qb, tb, ib) = r
    qa = [int(x) for x in qa]; qb = [int(x) for x in qb]
    if diff:
        dr, dg, db = ((qb[c] - qa[c]) & 7 for c in range(3))
        hi = (qa[0] << 27) | (dr << 24) | (qa[1] << 19) | (dg << 16) | (qa[2] << 11) | (db << 8)
    else:
        hi = (qa[0] << 28) | (qb[0] << 24) | (qa[1] << 20) | (qb[1] << 16) | (qa[2] << 12) | (qb[2] << 8)
    hi |= (int(ta) << 5) | (int(tb) << 2) | (diff << 1) | flip
    lo = 0
    for ks, idxs in ((subs[0], ia), (subs[1], ib)):
        for k, i in zip(ks, idxs):
            i = int(i)
            lo |= ((i >> 1) << (16 + k)) | ((i & 1) << k)
    return (hi << 32) | lo


def decode(b, w, h, fmt, off):
    im = Image.new('RGBA', (w, h))
    pix = im.load()
    if fmt in ('ETC1', 'ETC1A4'):
        p = off
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for bx, by in ((0, 0), (4, 0), (0, 4), (4, 4)):
                    a = None
                    if fmt == 'ETC1A4':
                        a = struct.unpack_from('<Q', b, p)[0]; p += 8
                    v = struct.unpack_from('<Q', b, p)[0]; p += 8
                    cols = etc1_decode_block(v)
                    for k in range(16):
                        x, y = k >> 2, k & 3
                        al = ((a >> (k * 4)) & 15) * 17 if a is not None else 255
                        pix[tx + bx + x, ty + by + y] = cols[k] + (al,)
    else:
        bpp = BPP[fmt]
        p = off
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for i in range(64):
                    x, y = MORTON[i]
                    if bpp == 4:
                        v = (b[p + i // 2] >> (4 * (i & 1))) & 15
                    elif bpp == 8:
                        v = b[p + i]
                    elif bpp == 16:
                        v = struct.unpack_from('<H', b, p + i * 2)[0]
                    else:
                        v = b[p + i * bpp // 8: p + (i + 1) * bpp // 8]
                    pix[tx + x, ty + y] = _px(fmt, v)
                p += 64 * bpp // 8
    return im


def _px(fmt, v):
    if fmt == 'RGBA8': return (v[3], v[2], v[1], v[0])
    if fmt == 'RGB8': return (v[2], v[1], v[0], 255)
    if fmt == 'RGBA5551':
        e = lambda c: (c << 3) | (c >> 2)
        return (e(v >> 11), e((v >> 6) & 31), e((v >> 1) & 31), 255 if v & 1 else 0)
    if fmt == 'RGB565':
        return (((v >> 11) << 3) | (v >> 13), (((v >> 5) & 63) << 2) | (((v >> 5) & 63) >> 4), ((v & 31) << 3) | ((v & 31) >> 2), 255)
    if fmt == 'RGBA4': return ((v >> 12) * 17, ((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17)
    if fmt == 'LA8': return (v >> 8, v >> 8, v >> 8, v & 255)
    if fmt == 'HILO8': return (v >> 8, v & 255, 0, 255)
    if fmt == 'L8': return (v, v, v, 255)
    if fmt == 'A8': return (255, 255, 255, v)
    if fmt == 'LA4': return ((v >> 4) * 17,) * 3 + ((v & 15) * 17,)
    if fmt == 'L4': return (v * 17, v * 17, v * 17, 255)
    if fmt == 'A4': return (255, 255, 255, v * 17)


def _enc_px(fmt, p):
    r, g, b_, a = p
    if fmt == 'RGBA8': return bytes((a, b_, g, r))
    if fmt == 'RGB8': return bytes((b_, g, r))
    if fmt == 'RGBA5551': return struct.pack('<H', ((r >> 3) << 11) | ((g >> 3) << 6) | ((b_ >> 3) << 1) | (1 if a >= 128 else 0))
    if fmt == 'RGB565': return struct.pack('<H', ((r >> 3) << 11) | ((g >> 2) << 5) | (b_ >> 3))
    if fmt == 'RGBA4': return struct.pack('<H', ((r // 17) << 12) | ((g // 17) << 8) | ((b_ // 17) << 4) | (a // 17))
    if fmt == 'LA8': return struct.pack('<H', (((r + g + b_) // 3) << 8) | a)
    if fmt == 'L8': return bytes(((r + g + b_) // 3,))
    if fmt == 'A8': return bytes((a,))
    if fmt == 'LA4': return bytes(((((r + g + b_) // 3) // 17) << 4 | (a // 17),))
    raise ValueError('format not supported for writing: ' + fmt)


def encode(im, w, h, fmt, orig=None):
    """orig=(байты исходной текстуры, её декодированная картинка): неизменённые блоки ETC копируются как есть."""
    im = im.convert('RGBA')
    assert im.size == (w, h), (im.size, (w, h))
    pix = im.load()
    out = bytearray()
    if fmt in ('ETC1', 'ETC1A4'):
        bsz = 16 if fmt == 'ETC1A4' else 8
        opix = orig[1].convert('RGBA').load() if orig else None
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for bx, by in ((0, 0), (4, 0), (0, 4), (4, 4)):
                    px = [pix[tx + bx + (k >> 2), ty + by + (k & 3)] for k in range(16)]
                    if opix is not None and px == [opix[tx + bx + (k >> 2), ty + by + (k & 3)] for k in range(16)]:
                        out += orig[0][len(out):len(out) + bsz]
                        continue
                    if fmt == 'ETC1A4':
                        a = 0
                        for k in range(16): a |= (round(px[k][3] / 17) & 15) << (k * 4)
                        out += struct.pack('<Q', a)
                    # цвет полностью прозрачных пикселей не важен: берём средний видимый
                    vis = [p for p in px if p[3] > 0] or px
                    avg = tuple(sum(p[c] for p in vis) // len(vis) for c in range(3))
                    rgb = [p[:3] if p[3] > 0 else avg for p in px]
                    out += struct.pack('<Q', etc1_encode_block(rgb))
    elif BPP[fmt] in (4,):
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                vals = []
                for i in range(64):
                    x, y = MORTON[i]; r, g, b_, a = pix[tx + x, ty + y]
                    vals.append(a // 17 if fmt == 'A4' else ((r + g + b_) // 3) // 17)
                for i in range(0, 64, 2): out.append(vals[i] | (vals[i + 1] << 4))
    else:
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for i in range(64):
                    x, y = MORTON[i]
                    out += _enc_px(fmt, pix[tx + x, ty + y])
    return bytes(out)


def main():
    cmd = sys.argv[1]
    b = open(sys.argv[2], 'rb').read()
    tx = textures(b)
    if cmd == 'list':
        for t in tx: print(*t[:4])
    elif cmd == 'dump':
        os.makedirs(sys.argv[3], exist_ok=True)
        for name, w, h, fmt, off, n in tx:
            decode(b, w, h, fmt, off).save(os.path.join(sys.argv[3], name + '.png'))
    elif cmd == 'put':
        name, png = sys.argv[3], sys.argv[4]
        out = sys.argv[5] if len(sys.argv) > 5 else sys.argv[2]
        bb = bytearray(b)
        hit = [t for t in tx if t[0] == name]
        assert hit, 'no texture ' + name
        for _, w, h, fmt, off, n in hit:
            data = encode(Image.open(png), w, h, fmt)
            assert len(data) == n, (len(data), n)
            bb[off:off + n] = data
        open(out, 'wb').write(bb)


if __name__ == '__main__':
    main()
