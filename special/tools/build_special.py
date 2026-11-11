"""Сборка русского текста RF4 Special.

Для каждой строки Special берётся (по приоритету):
  1. наш ручной перевод 3DS (сопоставление по английскому тексту с учётом порядка строк);
  2. правка из special/tr/<файл>.tsv (номер<TAB>перевод), если есть;
  3. машинный перевод из special/machine/ (с заменой имён по глоссарию);
  4. английский оригинал (если ничего нет).

  python3 special/tools/build_special.py SPECIAL_EN_DIR DS_EN_TEXT_DIR
    SPECIAL_EN_DIR  - папка с английскими .eng из RF4 Special
    DS_EN_TEXT_DIR  - папка с английскими .eng 3DS для файлов из text/ (Load, MapName и т. д.)
"""
import sys,os,re,difflib,json,textwrap,collections
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,os.path.join(ROOT,'tools'))
from rf4s_txt import read_eng,write_eng,read_txt
import openpyxl

SP_EN,DS_TEXT_EN=sys.argv[1],sys.argv[2]
OUT=os.path.join(ROOT,'special','Bundle'); TAB=os.path.join(ROOT,'special','tables'); TR=os.path.join(ROOT,'special','tr')
os.makedirs(OUT,exist_ok=True); os.makedirs(TAB,exist_ok=True)

def n2(x):
    x=re.sub(r"^''|''$","",x.strip()); x=re.sub(r'^＊','',x)
    x=x.replace("''","").replace('"','').replace('”','').replace('“','').replace('…','...')
    return re.sub(r'\s+',' ',x).strip()

# ---------- 3DS sources: (english list or None, russian list)
def xlsx_pairs(p,n):
    ws=openpyxl.load_workbook(p,read_only=True).active
    rows=list(ws.iter_rows(min_row=2,max_row=n+1,max_col=2,values_only=True))
    f=lambda v:'' if v is None else str(v).replace('\r\n','\n')
    return [f(a) for a,b in rows],[f(b) for a,b in rows]
def ds_source(f):
    if f=='rf3mc.eng':
        n=len(read_eng(os.path.join(ROOT,'script',f))[1]); return xlsx_pairs(os.path.join(ROOT,'script','rf3mc.eng.rus.xlsx'),n)
    x=os.path.join(ROOT,'textAndData','text',f+'.rus.xlsx')
    if os.path.exists(x):
        n=len(read_eng(os.path.join(ROOT,'textAndData','text',f))[1]); return xlsx_pairs(x,n)
    t=os.path.join(ROOT,'text',f)
    if os.path.exists(t) and os.path.exists(os.path.join(DS_TEXT_EN,f)):
        return read_eng(os.path.join(DS_TEXT_EN,f))[1],read_eng(t)[1]
    t=os.path.join(ROOT,'textAndData','text',f)
    if os.path.exists(t): return None,read_eng(t)[1]
    return None,None

# ---------- glossary for machine-translated lines
GLOSS=json.load(open(os.path.join(ROOT,'special','glossary.json'),encoding='utf-8')) if os.path.exists(os.path.join(ROOT,'special','glossary.json')) else {}
def gloss(x):
    for a,b in GLOSS.items(): x=re.sub(r'(?<![А-Яа-яЁё])'+a+r'(?![а-яё])',b,x)
    return x

# ---------- wrapping
TAGW=re.compile(r'＠‡([^,＠]*),([^＠]*)＠|＠[^＠]*＠')
def dlen(s):  # приблизительная длина на экране
    return len(TAGW.sub(lambda m: 'x'*max(len(m.group(1)),len(m.group(2))) if m.group(1) is not None else 'x'*8, s))
def wrap_to(ru,width):
    words=ru.replace('\n',' ').split(' '); lines=[];cur=''
    for w in words:
        if not w: continue
        t=(cur+' '+w) if cur else w
        if cur and dlen(t)>width: lines.append(cur); cur=w
        else: cur=t
    if cur: lines.append(cur)
    return '\n'.join(lines)
BOX=60
def adapt(sp,ds,ru):
    """Перевод 3DS -> строка Special: кавычки '' и ＊, перенос под ширину Special."""
    if sp==ds: return ru
    core=ru
    if sp.startswith("''") and sp.endswith("''") and len(sp)>4 and not core.startswith("''"):
        m=re.fullmatch(r'\s*[«"“](.*)[»"”]\s*',core,re.S)
        core="''"+(m.group(1) if m else core)+"''"
    if sp.startswith('＊') and not ds.startswith('＊') and not core.startswith('＊'): core='＊'+core
    if sp.replace('\n',' ')!=ds.replace('\n',' ') and n2(sp)!=n2(ds): return core
    if '\n' in ds and '\n\n' not in ru and '%' not in ds:
        if '\n' not in sp and dlen(core.replace('\n',' '))<=BOX: return core.replace('\n',' ')
        return wrap_to(core,BOX)
    return core

# ---------- новый перевод строк Special: special/tr/src.json + part*.tsv (номер<TAB>перевод)
TRMAP={}
if os.path.exists(os.path.join(TR,'src.json')):
    import glob
    _src=json.load(open(os.path.join(TR,'src.json'),encoding='utf-8'))
    for p in sorted(glob.glob(os.path.join(TR,'part*.tsv'))):
        for ln in open(p,encoding='utf-8'):
            ln=ln.rstrip('\n')
            if ln.strip():
                k,t=ln.split('\t',1); fk,ek=_src[int(k)]; TRMAP[(fk,ek)]=t.replace('\\n','\n')
TOK=re.compile(r'＠(?!‡)[^＠]*＠')
bad=0
for (fk,ek),t in TRMAP.items():
    if sorted(TOK.findall(ek))!=sorted(TOK.findall(t)) or ek.count('＋')!=t.count('＋') or ek.count('%')!=t.count('%'):
        print('TOKEN MISMATCH',fk,repr(ek),repr(t)); bad+=1
report=[]
for f in sorted(os.listdir(SP_EN)):
    if not f.endswith('.eng'): continue
    sp=read_eng(os.path.join(SP_EN,f))[1]
    ds_en,ds_ru=ds_source(f)
    mtp=os.path.join(ROOT,'special','machine',f); mtt=mtp+'.txt'
    mt=read_eng(mtp)[1] if os.path.exists(mtp) else (read_txt(mtt) if os.path.exists(mtt) else None)
    if mt is not None and len(mt)!=len(sp): mt=None
    edits={}
    tp=os.path.join(TR,f+'.tsv')
    if os.path.exists(tp):
        for ln in open(tp,encoding='utf-8'):
            ln=ln.rstrip('\n')
            if ln.strip(): i,t=ln.split('\t',1); edits[int(i)]=t.replace('\\n','\n')
    pair={}; approx=set()   # special idx -> 3DS idx
    if ds_en is not None:
        sm=difflib.SequenceMatcher(None,[n2(x) for x in sp],[n2(x) for x in ds_en],autojunk=False)
        for tag,a1,a2,b1,b2 in sm.get_opcodes():
            if tag=='equal':
                for k in range(a2-a1): pair[a1+k]=b1+k
            elif tag=='replace' and a2-a1==b2-b1:
                # строки на тех же местах: в таблице 3DS вместо английского уже стоял русский
                # или текст в Special слегка переписан
                for k in range(a2-a1):
                    x,y=sp[a1+k],ds_en[b1+k]
                    if re.search('[А-Яа-яЁё]',y) or difflib.SequenceMatcher(None,n2(x),n2(y)).ratio()>=0.75:
                        pair[a1+k]=b1+k; approx.add(a1+k)
        first={}
        for j,x in enumerate(ds_en): first.setdefault(n2(x),j)
        for i,x in enumerate(sp):
            if i not in pair and n2(x) in first and x.strip(): pair[i]=first[n2(x)]
    elif ds_ru is not None:
        if len(ds_ru)==len(sp): pair={i:i for i in range(len(sp))}
        elif mt is not None:   # выравнивание по совпадающим строкам машинного и нашего перевода
            sm=difflib.SequenceMatcher(None,[x.lower() for x in mt],[x.lower() for x in ds_ru],autojunk=False)
            prev=(0,0)
            for a,b,z in sm.get_matching_blocks():
                ga,gb=a-prev[0],b-prev[1]
                if ga==gb:
                    for k in range(ga): pair[prev[0]+k]=prev[1]+k
                for k in range(z): pair[a+k]=b+k
                prev=(a+z,b+z)
    out=[];src=[]
    for i,x in enumerate(sp):
        if i in edits: out.append(edits[i]); src.append('правка')
        elif i in pair and ds_ru[pair[i]]!='':
            j=pair[i]; ru=ds_ru[j]
            out.append(adapt(x,ds_en[j],ru) if ds_en is not None else ru); src.append('3DS≈' if i in approx else '3DS')
        elif not x: out.append(''); src.append('пусто')
        elif (f,x) in TRMAP: out.append(TRMAP[(f,x)]); src.append('перевод')
        elif mt is not None and mt[i]: out.append(gloss(mt[i])); src.append('машинный')
        elif not re.search('[A-Za-z]',x): out.append(x); src.append('служебное')
        else: out.append(x); src.append('англ.')
    if f=='rf3mc.eng':   # слишком длинные строки диалогов переносим под ширину окна
        for i,x in enumerate(out):
            if '%' not in x and any(dlen(l)>BOX+4 and ' ' in l for l in x.split('\n')):
                out[i]='\n'.join(wrap_to(l,BOX) if dlen(l)>BOX+4 else l for l in x.split('\n'))
    write_eng(os.path.join(OUT,f),b'TEXT',out)
    assert read_eng(os.path.join(OUT,f))[1]==out
    wb=openpyxl.Workbook(); ws=wb.active; ws.title=f[:-4][:31]
    ws.append(['№','English (Special)','Русский','Источник'])
    for i,(a,b,c) in enumerate(zip(sp,out,src)): ws.append([i,a,b,c])
    ws.column_dimensions['B'].width=60; ws.column_dimensions['C'].width=60
    wb.save(os.path.join(TAB,f+'.xlsx'))
    c=collections.Counter(src); report.append((f,len(sp),c))
    print(f'{f:45} {len(sp):6}  '+'  '.join(f'{k}:{v}' for k,v in c.most_common()))
