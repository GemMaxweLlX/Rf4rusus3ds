"""Сборка русских текстур 3DS из английских оригиналов.

  python3 tools/tex_build.py SRC_DIR OUT_DIR [PREVIEW.png]
    SRC_DIR - папка с английскими текстурами 3DS (font/, menu/, menu_field/ ...)
    OUT_DIR - куда положить изменённые файлы (та же структура папок)
Каждая запись JOBS: файл, имя текстуры, функция правки картинки (в горизонтальном виде).
"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctr_tex
from tex_ru import *

SRC = None
PC_CAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'textures', 'pc_calendar')
JOBS = []   # (относительный путь, имя текстуры, поворот, функция)


def job(path, name, rot=0):
    def deco(fn):
        JOBS.append((path, name, rot, fn)); return fn
    return deco


# ---------- подсказки кнопок на нижнем экране (A PLACE, B EAT ...): 64x16, повёрнуты
# Тело кнопки одинаковое у всех, чистый образец берём с «B EAT» (там текст короткий).
ITEM_HELP = {'00': 'КЛАСТЬ', '01': 'ВНУТРЬ', '02': 'ДАТЬ', '03': 'КИНУТЬ', '04': 'ВЗЯТЬ', '05': 'ШВЫРЬ',
             '06': 'ОСМОТР', '07': 'НАДЕТЬ', '08': 'СЪЕСТЬ', '09': 'УДАР', '09_b': 'ЛОВИТЬ', '10': 'НАДЕТЬ',
             '11': 'УБРАТЬ', '12': 'ВЗМАХ', '13': 'НАДЕТЬ', '14': 'УБРАТЬ', '15': 'ВЗМАХ'}
_IH_CLEAN = {}


def _ih_clean(src):
    if 'im' not in _IH_CLEAN:
        b = open(os.path.join(src, 'font/item_help01_08.bctex'), 'rb').read()
        t = ctr_tex.textures(b)[0]
        im = ctr_tex.decode(b, *t[1:5]).rotate(90, expand=True)
        fill_columns(im, (14, 0, 35, 16), 16)          # стереть «EAT», оставить тело и закругление
        _IH_CLEAN['im'] = im
    return _IH_CLEAN['im']


for n, t in ITEM_HELP.items():
    def f(im, t=t, src=None):
        clean = _ih_clean(SRC)
        im.paste(clean.crop((14, 0, 64, 16)), (14, 0))
        draw_text(im, (15, 2, 40, 14), t, height=6.4, stroke_w=0.9, stroke=(10, 35, 40, 255), max_squeeze=0.45)
    job(f'font/item_help01_{n}.bctex', f'item_help01_{n}_00', 90)(f)


# ---------- серые кнопки сортировки 64x16 (Sort, Auto, Category, Skill, Size, Gold)
SORT_STYLE = dict(height=7.6, stroke_w=1.0, stroke=(55, 75, 95, 255), font='black', max_squeeze=0.55)
SORT = [('menu/itemContainer_button_sort.bcmdl', 'itemContainer_button_sort_%s_00', 'Порядок', 17)]
for k in ('autoDesc', 'autoAsc'):
    SORT += [('menu/campmenu_friendship_button_sort.bcmdl', f'campmenu_friendship_button_sort_{k}_%s_00', 'Авто', 18),
             ('menu/shipmentData_button_sort.bcmdl', f'shipmentData_button_sort_{k}_%s_00', 'Авто', 18)]
for k, t in (('valueDesc', 'Цена'), ('valueAsc', 'Цена'), ('sizeDesc', 'Размер'), ('sizeAsc', 'Размер')):
    SORT.append(('menu/shipmentData_button_sort.bcmdl', f'shipmentData_button_sort_{k}_%s_00', t, 17))
SORT += [('menu/recipeMenu_recipeList_button_sort.bcmdl', 'recipeMenu_recipeList_button_sort_category_%s_00', 'Категория', 4),
         ('menu/recipeMenu_recipeList_button_sort.bcmdl', 'recipeMenu_recipeList_button_sort_skillAsc_%s_00', 'Навык', 17),
         ('menu/recipeMenu_recipeList_button_sort.bcmdl', 'recipeMenu_recipeList_button_sort_skillDesc_%s_00', 'Навык', 17)]
for path, name, t, x0 in SORT:
    for st in ('pop', 'push'):
        def f(im, t=t, x0=x0):
            x1 = right_edge(im, 8) - 3
            fill_columns(im, (x0, 2, x1, 14), x1)
            draw_text(im, (x0, 2, x1, 14), t, **SORT_STYLE)
        job(path, name % st, 90)(f)


# ---------- розовые/синие кнопки магазина и кузницы 64x32 (Y BUY, X RESET, A Skip)
# Стираем только буквы (белые + их тень), каждую строку заливаем цветом тела кнопки из этой же строки;
# закруглённый край кнопки не трогаем. Русский текст белый, без чёрной обводки, как в оригинале.
def body_fill(im, mask, x0, x1, left=True):
    px = im.load()
    for y in {p[1] for p in mask}:
        bg = [px[x, y] for x in range(x0, x1) if (x, y) not in mask and px[x, y][3] > 230]
        if len(bg) < 3:   # вся строка занята буквами - берём фон сразу за краями области
            side = (list(range(max(0, x0 - 3), x0)) if left else []) + list(range(x1, min(im.width, x1 + 2)))
            bg = [px[x, y] for x in side if px[x, y][3] > 230] or bg   # left=False: слева значок, берём только справа
        if not bg: continue
        bg.sort(key=lambda p: sum(p[:3])); mid = bg[len(bg) // 2]
        for x in range(x0, x1):
            if (x, y) in mask: px[x, y] = mid
    return im


for path, name, t, shade in (('menu/shop_button.bcmdl', 'shop_button_buy_%s_00', 'КУПИТЬ', (175, 40, 95, 255)),
                             ('menu/shop_button.bcmdl', 'shop_button_reset_%s_00', 'СБРОС', (35, 80, 160, 255)),
                             ('menu/synthesis_button.bcmdl', 'synthesis_button_dialogSkip_%s_00', 'Пропуск', (175, 40, 95, 255))):
    for st in ('pop', 'push'):
        def f(im, t=t, shade=shade):
            x1 = right_edge(im, 11) - 4                                   # до закругления
            m = outlined_text_mask(im, (17, 3, x1, 20), lambda r, g, b, a: a > 200 and min(r, g, b) > 185,
                                   lambda r, g, b, a: a > 200 and r + g + b < 360, reach=1)
            body_fill(im, m, 17, x1)
            draw_text(im, (18, 4, x1 - 1, 19), t, height=9.5, stroke_w=0.6, color=(255, 255, 255, 255),
                      stroke=shade, font='xbold', max_squeeze=0.6)
        job(path, name % st, 90)(f)


# ---------- категории в меню дружбы 64x32 (PPL, MON): жёлтая (pop) и бирюзовая (push) кнопки
# Буквы стираем построчно цветом тела кнопки (как у кнопок магазина), текст ставим ниже - по строке оригинала.
for name, t in (('campmenu_friendship_button_category_npc_%s_00', 'ЛЮДИ'), ('campmenu_friendship_button_category_monster_%s_00', 'ЗВЕРИ')):
    for st in ('pop', 'push'):
        def f(im, t=t, st=st, name=name):
            x1 = right_edge(im, 14) - 4
            x0 = 23 if 'monster' in name else 25
            if st == 'pop':
                fill = lambda r, g, b, a: a > 200 and b > 115
                col, stroke = (255, 250, 228, 255), (165, 115, 35, 255)
            else:
                fill = lambda r, g, b, a: a > 200 and min(r, g, b) > 150
                col, stroke = (255, 255, 255, 255), (25, 60, 70, 255)
            m = outlined_text_mask(im, (x0, 5, x1, 21), fill, lambda r, g, b, a: a > 200 and r + g + b < 330, reach=2)
            body_fill(im, m, x0, x1, left=False)
            draw_text(im, (x0 + 3, 8, x1, 20), t, height=8, stroke_w=0.8, color=col, stroke=stroke, font='black', max_squeeze=0.6)
        job('menu/campmenu_friendship_button_category.bcmdl', name % st, 90)(f)


# ---------- дни недели в календаре 32x16
DAYS = {'01': ('ВЫХ', (215, 95, 105, 255), (90, 20, 30, 255)), '02': ('ПН', None, None), '03': ('ВТ', None, None),
        '04': ('СР', None, None), '05': ('ЧТ', None, None), '06': ('ПТ', None, None)}
for n, (t, col, st) in DAYS.items():
    def f(im, t=t, col=col, st=st):
        clear(im)
        draw_text(im, (1, 1, 31, 15), t, height=11, stroke_w=1.3, color=col or (225, 240, 245, 255),
                  stroke=st or (30, 50, 70, 255), font='black', max_squeeze=0.7)
    job(f'font/font_7days_{n}.bctex', f'font_7days_{n}_00', 90)(f)


# ---------- заголовки «LOAD»/«SAVE» на пере 256x32
for path, name, t in (('menu_field/title_header_load.bctex', 'title_header_load_00', 'ЗАГРУЗКА'),
                      ('menu_field/title_header_save.bctex', 'title_header_save_00', 'СОХРАНЕНИЕ')):
    def f(im, t=t):
        text = lambda r, g, b, a: min(r, g, b) > 185 or (r + g + b) < 330 or (g - r < 25 and g < 170)
        erase_text_by_column(im, (88, 3, 182, 25), text)
        draw_text(im, (92, 6, 178, 21), t, height=9, stroke_w=1.2, color=(240, 252, 235, 255),
                  stroke=(30, 95, 90, 255), font='black', max_squeeze=0.75)
    job(path, name, 90)(f)


# ---------- ON/OFF в настройках 64x16
for name, t in (('campmenu_config_item_on_00', 'ВКЛ'), ('campmenu_config_item_off_00', 'ВЫКЛ')):
    def f(im, t=t):
        x1 = right_edge(im, 8) - 4
        fill_columns(im, (12, 2, x1, 13), 10)
        draw_text(im, (12, 2, x1, 13), t, height=7.6, stroke_w=1.0, color=(255, 255, 255, 255),
                  stroke=(25, 70, 85, 255), font='black', max_squeeze=0.7)
    job('menu/campmenu_config_item.bcmdl', name, 90)(f)


# ---------- кнопки экрана ввода имени 64x32 (ERASE, ENTER)
for name, t, stroke in (('nameEntry_button_backspace_%s_00', 'СТЕРЕТЬ', (70, 70, 70, 255)),
                        ('nameEntry_button_decision_%s_00', 'ГОТОВО', (90, 40, 25, 255))):
    for st in ('pop', 'push'):
        def f(im, t=t, stroke=stroke):
            x1 = right_edge(im, 11) - 5
            text = lambda r, g, b, a: min(r, g, b) > 170 or (max(r, g, b) - min(r, g, b) < 18 and r > 140)
            erase_text_by_column(im, (6, 4, x1, 19), text)
            draw_text(im, (7, 4, x1, 19), t, height=9, stroke_w=0.8, color=(245, 245, 245, 255), stroke=stroke,
                      font='black', max_squeeze=0.65)
        job('menu/nameEntry_button.bcmdl', name % st, 90)(f)


# ---------- подсказка на экране ввода имени 128x64 (L R INPUT / START ENTER / Y SWITCH)
# Стираем буквы построчно цветом полоски (розовой или серой), текст вписываем до закругления справа.
for name in ('nameEntry_help_kanjiEnable_00', 'nameEntry_help_kanjiDisable_00'):
    def f(im, name=name):
        for (y0, y1), t in (((2, 20), 'НАБОР'), ((22, 41), 'ГОТОВО'), ((43, 62), 'СМЕНА')):
            x1 = right_edge(im, (y0 + y1) // 2) - 3
            grey = 'Disable' in name and y0 == 43
            hi, lo = (165, 130) if grey else (85, 38)      # светлые буквы и их тень относительно цвета полоски
            m = outlined_text_mask(im, (36, y0 + 2, x1, y1 - 2), lambda r, g, b, a, hi=hi: a > 150 and min(r, g, b) > hi,
                                   lambda r, g, b, a, lo=lo: a > 150 and min(r, g, b) < lo, reach=2)
            body_fill(im, m, 36, x1)                        # клавиши L/R/START заканчиваются на x=34
            draw_text(im, (42, y0 + 4, x1 - 4, y1 - 3), t, height=10, stroke_w=0.7, color=(255, 255, 255, 255),
                      stroke=(130, 130, 130, 255) if grey else (175, 45, 95, 255), font='xbold', max_squeeze=0.6)
    job('menu/nameEntry.bcmdl', name, 90)(f)


# ---------- «Materials» на свитке в окне рецептов (128x256, надпись вертикальная)
def _dark_text(r, g, b, a): return (r + g + b) < 480


@job('menu/recipeMenu.bcmdl', 'recipeMenu_materialList_00', 90)
def _(im):
    box = rbox((85, 2, 106, 47), 128)
    erase_text_by_row(im, box, _dark_text)
    draw_text(im, box, 'Материалы', height=7.5, stroke_w=0, color=(70, 55, 30, 255), stroke=(0, 0, 0, 0),
              font='bold', max_squeeze=0.75)


@job('menu/recipeMenu.bcmdl', 'recipeMenu_recipeList_00', 90)
def _(im):
    box = rbox((48, 21, 61, 91), 256)
    erase_text_by_row(im, box, lambda r, g, b, a: (r + g + b) < 560)
    draw_text(im, box, 'Нужно RP', height=8.5, stroke_w=0, color=(80, 70, 60, 255), stroke=(0, 0, 0, 0),
              font='semibold', max_squeeze=0.8)


@job('menu/synthesis.bcmdl', 'synthesis_material6_00', 90)
def _(im):
    b1 = rbox((36, 4, 50, 50), 128)                         # «RP Used»
    inpaint(im, text_mask(im, b1, lambda r, g, b, a: a > 150 and (r + g + b) < 600, grow=1), iters=40)
    draw_text(im, b1, 'Расход RP', height=8.5, stroke_w=0, color=(70, 70, 70, 255), stroke=(0, 0, 0, 0), font='medium', max_squeeze=0.75, align='left')
    b2 = rbox((97, 1, 114, 48), 128)                        # «Materials» голубым
    erase_text_by_row(im, b2, lambda r, g, b, a: b - r > 40 and r < 200)
    draw_text(im, (b2[0] + 1, b2[1], b2[2] - 2, b2[3]), 'Материалы', height=7.5, stroke_w=0, color=(90, 160, 210, 255),
              stroke=(0, 0, 0, 0), font='bold', max_squeeze=0.45)
    b3 = rbox((65, 29, 79, 49), 128)                        # «Pcs.»
    erase_text_by_row(im, b3, lambda r, g, b, a: g - r > 25 and g - b > 10)
    draw_text(im, b3, 'шт.', height=6, stroke_w=0, color=(80, 160, 80, 255), stroke=(0, 0, 0, 0), font='bold', max_squeeze=0.8)


# ---------- окно улучшения в кузнице (256x256): Upgr Item, Materials, RP Used, Projected
@job('menu/synthesis.bcmdl', 'synthesis_material2_00', 90)
def _(im):
    for box, t, h in (((178, 64, 191, 130), 'Предмет', 8.5), ((225, 64, 238, 130), 'Материалы', 8.5)):
        b = rbox(box, 256)
        erase_text_by_row(im, b, lambda r, g, b_, a: (r + g + b_) < 520)
        draw_text(im, b, t, height=h, stroke_w=0, color=(70, 50, 40, 255), stroke=(0, 0, 0, 0), font='bold', max_squeeze=0.75)
    b = rbox((94, 4, 107, 50), 256)
    erase_text_by_row(im, b, lambda r, g, b_, a: (r + g + b_) < 500)
    draw_text(im, b, 'Расход RP', height=8.5, stroke_w=0, color=(60, 60, 60, 255), stroke=(0, 0, 0, 0), font='semibold', max_squeeze=0.75)


@job('menu/synthesis.bcmdl', 'synthesis_material2_00', 90)
def _(im):
    b = rbox((132, 60, 147, 124), 256)
    erase_text_by_row(im, b, lambda r, g, b_, a: min(r, g, b_) > 160)
    draw_text(im, b, 'Результат', height=8.5, stroke_w=0, color=(255, 250, 240, 255), stroke=(0, 0, 0, 0), font='bold', max_squeeze=0.75)


# ---------- календарь: название сезона на листе (верхний экран, 512x256 после поворота)
# Оригинал написан «руническим» шрифтом вдоль нижнего края листа: дуга «улыбкой», правый край выше.
# Дуга снята с оригинала (низ букв): окружность с центром (275, -4), радиус 68, от -14° до +41°.
CAL = {'0_spring': ('ВЕСНА', (40, 95, 40, 255), 250), '1_summer': ('ЛЕТО', (55, 60, 125, 255), 250),
       '2_autumn': ('ОСЕНЬ', (115, 55, 40, 255), 250), '3_winter': ('ЗИМА', (125, 45, 90, 255), 262)}
for f, (t, stroke, x0) in CAL.items():
    def top(im, t=t, stroke=stroke, x0=x0):
        lum = lambda r, g, b: r + g + b
        m = outlined_text_mask(im, (x0, 30, 336, 68), lambda r, g, b, a: a > 200 and lum(r, g, b) > 575,
                               lambda r, g, b, a: a > 200 and lum(r, g, b) < 420, reach=2)
        inpaint(im, m, iters=80)
        draw_smile_text(im, (275, -4), 68, -14, 41, t, 11, (255, 252, 245, 255), stroke, stroke_w=1.3)
    job(f'menu/calendar_{f}.bcmdl', f'calendar_{f}_top_00', 90)(top)


# ---------- кнопки календаря 64x64: крупная аббревиатура сезона + «MONTH >» / «< MONTH»
ABBR = {'0_spring': 'ВЕС', '1_summer': 'ЛЕТ', '2_autumn': 'ОСЕ', '3_winter': 'ЗИМ'}
ABBR_COL = {'0_spring': (70, 150, 70, 255), '1_summer': (20, 135, 145, 255), '2_autumn': (165, 85, 60, 255), '3_winter': (105, 85, 165, 255)}
ORDER = ['0_spring', '1_summer', '2_autumn', '3_winter']


def _dark_color(im, box, thr=400):
    px = im.load(); x0, y0, x1, y1 = box
    c = [px[x, y] for x in range(x0, x1) for y in range(y0, y1) if px[x, y][3] > 200 and sum(px[x, y][:3]) < thr]
    if not c: return (40, 40, 40, 255)
    c.sort(key=lambda p: sum(p[:3]))
    m = c[len(c) // 2]
    return (m[0], m[1], m[2], 255)


for i, f in enumerate(ORDER):
    for kind in ('next', 'prev'):
        other = ORDER[(i + 1) % 4] if kind == 'next' else ORDER[(i - 1) % 4]
        for st in ('pop', 'push'):
            def btn(im, f=f, kind=kind, st=st):
                # верх кнопки (фон в клетку + аббревиатура сезона + значок) берём с переведённой ПК-кнопки:
                # там тот же рисунок и почти те же пропорции (184x74 против 61x24)
                pc = Image.open(os.path.join(PC_CAL, f'calendar_{f}_button_{kind}_{st}_eng.png')).convert('RGBA')
                top = pc.crop((4, 4, 184, 76)).resize((59, 23), Image.LANCZOS)
                im.paste(top, (2, 2))
                # нижняя полоска: «MONTH >» -> «МЕСЯЦ >», «< MONTH» -> «< МЕСЯЦ», ровно на месте английского
                mbox = (3, 27, 37, 39) if kind == 'next' else (15, 27, 58, 39)   # стираем и стрелки «>»/«<»
                # порог - относительно фона полоски (у нажатой кнопки всё светлее)
                px = im.load()
                lum = lambda p: p[0] + p[1] + p[2]
                strip = sorted(lum(px[x, y]) for x in range(mbox[0], mbox[2]) for y in range(mbox[1], mbox[3]) if px[x, y][3] > 200)
                bgl = strip[len(strip) * 3 // 4]
                is_txt = lambda r, g, b, a: a > 200 and r + g + b < bgl - 45
                txt = sorted((px[x, y] for x in range(mbox[0], mbox[2]) for y in range(mbox[1], mbox[3]) if is_txt(*px[x, y])), key=lum)
                mcol = txt[len(txt) // 4] if txt else (90, 90, 100, 255)
                mcol = (mcol[0], mcol[1], mcol[2], 255)
                # стираем слово и стрелку (у «next» стрелка правее, до кнопки R)
                ebox = (3, 27, 41, 39) if kind == 'next' else (16, 27, 59, 39)
                inpaint(im, text_mask(im, ebox, is_txt, grow=1), iters=50)
                # бледная стрелка у нажатой кнопки - мягче порог
                arr = (34, 27, 43, 39) if kind == 'next' else (16, 27, 23, 39)
                inpaint(im, text_mask(im, arr, lambda r, g, b, a: a > 200 and r + g + b < bgl - 15, grow=1), iters=50)
                draw_text(im, (4, 28, 36, 38) if kind == 'next' else (22, 28, 59, 38), 'МЕСЯЦ',
                          height=7.5, stroke_w=0, color=mcol, stroke=(0, 0, 0, 0), font='bold', max_squeeze=0.75,
                          align='left' if kind == 'next' else 'center')
            job(f'menu/calendar_{f}.bcmdl', f'calendar_{f}_button_{kind}_{st}_00', 90)(btn)


# ---------- календарь: дни недели на репках в шапке (нижний экран)
WEEK = [(125, 'ВЫХ'), (176, 'ПН'), (226, 'ВТ'), (276, 'СР'), (327, 'ЧТ'), (377, 'ПТ')]
for f in ORDER:
    def bottom(im):
        for cx, t in WEEK:
            box = (cx - 9, 29, cx + 11, 38)
            m = text_mask(im, box, lambda r, g, b, a: a > 200 and (max(r, g, b) - min(r, g, b) > 30 or r + g + b < 600), grow=0)
            px = im.load()
            cols = sorted((px[x, y] for x, y in m), key=lambda p: sum(p[:3]))
            col = cols[len(cols) // 6] if cols else (90, 140, 90, 255)
            inpaint(im, m, iters=30)
            draw_text(im, (box[0], 29, box[2], 38), t, height=6.5, stroke_w=0, color=(col[0], col[1], col[2], 255),
                      stroke=(0, 0, 0, 0), font='black', max_squeeze=0.7)
    job(f'menu/calendar_{f}.bcmdl', f'calendar_{f}_bottom_00', 90)(bottom)


@job('menu/questboard.bcmdl', 'questboard_icon_now_00', 90)
def _(im):
    box = (6, 7, 27, 21)
    m = text_mask(im, box, lambda r, g, b, a: a > 150 and r - g > 50, grow=0)
    inpaint(im, m, iters=30)
    draw_text(im, (5, 8, 28, 20), 'ИДЁТ', height=7, stroke_w=0, color=(215, 40, 60, 255), stroke=(0, 0, 0, 0),
              font='black', max_squeeze=0.7)


def _fwd(im, rot):
    if rot == 'TV': return im.transpose(Image.TRANSVERSE)
    return im.rotate(rot, expand=True) if rot else im


def _back(im, rot):
    if rot == 'TV': return im.transpose(Image.TRANSVERSE)
    return im.rotate(-rot, expand=True) if rot else im


def build(src, out, preview=None):
    global SRC
    SRC = src
    shown = []
    by_file = {}
    for path, name, rot, fn in JOBS:
        by_file.setdefault(path, []).append((name, rot, fn))
    for path, items in by_file.items():
        b = bytearray(open(os.path.join(src, path), 'rb').read())
        tx = {t[0]: t for t in ctr_tex.textures(bytes(b))}
        for name, rot, fn in items:
            _, w, h, fmt, off, n = tx[name]
            im = ctr_tex.decode(bytes(b), w, h, fmt, off)
            orig = im.copy()
            hz = _fwd(im, rot)
            fn(hz)
            im = _back(hz, rot)
            data = ctr_tex.encode(im, w, h, fmt, (bytes(b[off:off + n]), orig))
            assert len(data) == n
            b[off:off + n] = data
            shown.append((_fwd(orig, rot), _fwd(ctr_tex.decode(data, w, h, fmt, 0), rot)))
        dst = os.path.join(out, path); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(b)
    if preview and shown:
        z = 6
        W = max(a.width for a, _ in shown) * z * 2 + 30
        H = sum(a.height * z + 8 for a, _ in shown)
        sh = Image.new('RGBA', (W, H), (60, 60, 60, 255)); y = 0
        for a, c in shown:
            sh.alpha_composite(a.resize((a.width * z, a.height * z), Image.NEAREST), (0, y))
            sh.alpha_composite(c.resize((c.width * z, c.height * z), Image.NEAREST), (W // 2 + 10, y))
            y += a.height * z + 8
        sh.save(preview)
    return len(shown)


if __name__ == '__main__':
    print('textures', build(*sys.argv[1:4]))
