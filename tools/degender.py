"""Замена игровой метки пола ＠‡мужская,женская＠ на форму «сделал(а)» — для 3DS,
где метка не работает (на Steam/Switch она работает, там её оставляем).

  сделал / сделала     -> сделал(а)
  новенький / новенькая -> новенький(ая)
  пришёл / пришла      -> пришёл(ла)
  Принца / Принцессы   -> Принца/Принцессы  (сильно разные слова пишем через косую черту)

  python3 tools/degender.py IN.xlsx COL ROW OUT.xlsx [WIDTH LINES]
    WIDTH/LINES (по умолчанию 40 и 3): строки, ставшие длиннее, переносятся заново.
"""
import re
import sys

TAG = re.compile(r'＠‡([^,＠]*),([^＠]*)＠')


def pair(m, cap=False):
    a, b = m.group(1), m.group(2)
    if not a or not b:
        return a or b
    p = 0
    while p < min(len(a), len(b)) and a[p].lower() == b[p].lower():
        p += 1
    # общая часть заканчивается на согласной перед «ёл»/«ел»: пришёл/пришла -> приш + ёл/ла
    ra, rb = a[p:], b[p:]
    if ra and rb and len(a) <= 4:         # короткие слова: этот/эта, тому/той
        return f'{a}/{b}'
    if ra and len(rb) == 1 and p > 2:     # сумасшедшему/сумасшедшей -> сумасшедшему(ей)
        p -= 1; ra, rb = a[p:], b[p:]
    if not ra:
        return f'{a}({rb})'
    if len(rb) <= 3 and len(ra) <= 3 and p >= 2:
        return f'{a}({rb})'
    return f'{a}/{b}'


# строки, которые после замены не влезают в окно 40x3: сокращённый вариант
FIX = {'А? Я ничему не научился(ась). Может быть, мне стоит ＋потренироваться в ковке и использовании инструментов＋ ещё немного.':
       'А? Ничему не научился(ась). Может,\nмне стоит ＋потренироваться в ковке и\nиспользовании инструментов＋ ещё немного.'}


def convert(s):
    if not isinstance(s, str):
        return s
    t = TAG.sub(pair, s)
    return FIX.get(' '.join(t.split()), t)


TAGW = re.compile(r'＠[^＠]*＠')


def dlen(s):
    return len(TAGW.sub('X' * 7, s).replace('＋', ''))


def rewrap(s, W, L):
    lines = s.split('\n')
    if max(dlen(l) for l in lines) <= W:
        return s
    words, out, cur = s.replace('\n', ' ').split(' '), [], ''
    for w in words:
        if not w:
            continue
        c = (cur + ' ' + w) if cur else w
        if cur and dlen(c) > W:
            out.append(cur); cur = w
        else:
            cur = c
    if cur:
        out.append(cur)
    return '\n'.join(out) if len(out) <= max(L, len(lines)) else s


if __name__ == '__main__':
    import openpyxl
    src, col, row, dst = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    W = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    L = int(sys.argv[6]) if len(sys.argv) > 6 else 3
    wb = openpyxl.load_workbook(src)
    ws = wb.active
    ci = openpyxl.utils.column_index_from_string(col)
    n = 0
    for r in range(row, ws.max_row + 1):
        v = ws.cell(r, ci).value
        if isinstance(v, str) and '‡' in v:
            ws.cell(r, ci).value = rewrap(convert(v), W, L)
            n += 1
    wb.save(dst)
    print('converted rows', n)
