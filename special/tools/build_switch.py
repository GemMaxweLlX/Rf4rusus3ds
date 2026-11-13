"""Сборка русского текста RF4 Special для Nintendo Switch.

Тексты Switch почти совпадают со Steam. Для каждой строки:
  1. если такая же английская строка есть в Steam (с учётом порядка) - берём готовый русский из special/Bundle;
  2. иначе - результат обычной сборки build_special.py по английскому тексту Switch
     (перевод 3DS, наши переводы, MonkaKarlo, английский).
  3. правки только для Switch: special/switch/tr/<файл>.tsv (номер<TAB>перевод).

  python3 special/tools/build_switch.py SWITCH_ROMFS STEAM_EN_DIR DS_EN_TEXT_DIR
    SWITCH_ROMFS  - папка romfs Switch (script/, text/, textAndData/text/) с английскими .eng
    STEAM_EN_DIR  - папка с английскими .eng из Steam-версии (как для build_special.py)
    DS_EN_TEXT_DIR - то же, что второй аргумент build_special.py
Результат: special/switch/romfs/... (готово для atmosphere/contents/<TitleID>/romfs)
           special/switch/tables/*.xlsx (сверка: английский, русский, источник)
"""
import sys, os, re, difflib, subprocess, tempfile, shutil, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from rf4s_txt import read_eng, write_eng
import openpyxl

SW, ST_EN, DS_EN = sys.argv[1:4]
STEAM_RU = os.path.join(ROOT, 'special', 'Bundle')
OUT = os.path.join(ROOT, 'special', 'switch', 'romfs')
TAB = os.path.join(ROOT, 'special', 'switch', 'tables')
TR = os.path.join(ROOT, 'special', 'switch', 'tr')
os.makedirs(TAB, exist_ok=True)

def n2(x):
    return re.sub(r'\s+', ' ', x.replace('\r', '')).strip()

files = {}
for d, _, fs in os.walk(SW):
    for f in fs:
        if f.endswith('.eng'):
            files[f] = os.path.relpath(os.path.join(d, f), SW)

tmp = tempfile.mkdtemp()
flat = os.path.join(tmp, 'en'); os.makedirs(flat)
for f, rel in files.items():
    shutil.copy(os.path.join(SW, rel), os.path.join(flat, f))
env = dict(os.environ, RF4S_HPRP='0', RF4S_OUT=os.path.join(tmp, 'raw'), RF4S_TAB=os.path.join(tmp, 'rawtab'))
subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'special', 'tools', 'build_special.py'), flat, DS_EN],
               env=env, check=True, stdout=subprocess.DEVNULL)

for f in sorted(files):
    sw = read_eng(os.path.join(SW, files[f]))[1]
    st = read_eng(os.path.join(ST_EN, f))[1]
    st_ru = read_eng(os.path.join(STEAM_RU, f))[1]
    raw = read_eng(os.path.join(tmp, 'raw', f))[1]
    rawsrc = [r[3].value for r in openpyxl.load_workbook(os.path.join(tmp, 'rawtab', f + '.xlsx'), read_only=True).active.iter_rows(min_row=2)]
    edits = {}
    tp = os.path.join(TR, f + '.tsv')
    if os.path.exists(tp):
        for ln in open(tp, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if ln.strip():
                i, t = ln.split('\t', 1); edits[int(i)] = t.replace('\\n', '\n')
    pair = {}
    sm = difflib.SequenceMatcher(None, [n2(x) for x in sw], [n2(x) for x in st], autojunk=False)
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(a2 - a1): pair[a1 + k] = b1 + k
    out, src = [], []
    for i, x in enumerate(sw):
        if i in edits: out.append(edits[i]); src.append('правка Switch')
        elif i in pair:   # на Switch панель английская: ОЗ/ОР из Steam-перевода обратно в HP/RP
            out.append(re.sub('(?<![А-Яа-яЁё])ОЗ(?![А-Яа-яЁё])', 'HP', re.sub('(?<![А-Яа-яЁё])ОР(?![А-Яа-яЁё])', 'RP', st_ru[pair[i]]))); src.append('Steam')
        else: out.append(raw[i]); src.append(rawsrc[i])
    p = os.path.join(OUT, files[f]); os.makedirs(os.path.dirname(p), exist_ok=True)
    write_eng(p, b'TEXT', out)
    assert read_eng(p)[1] == out
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = f[:-4][:31]
    ws.append(['№', 'English (Switch)', 'Русский', 'Источник'])
    for i, (a, b, c) in enumerate(zip(sw, out, src)): ws.append([i, a, b, c])
    ws.column_dimensions['B'].width = 60; ws.column_dimensions['C'].width = 60
    wb.save(os.path.join(TAB, f + '.xlsx'))
    c = collections.Counter(src)
    print(f'{files[f]:55} {len(sw):6}  ' + '  '.join(f'{k}:{v}' for k, v in c.most_common()))
shutil.rmtree(tmp)
