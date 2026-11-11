import openpyxl,re,json,sys,glob,textwrap,os
S=sys.argv[1]
src=json.load(open(S+'/tr/src.json'))
tr={}
for f in sorted(glob.glob(S+'/tr/part*.tsv')):
    for ln in open(f,encoding='utf-8'):
        ln=ln.rstrip('\n')
        if not ln.strip(): continue
        i,t=ln.split('\t',1); tr[int(i)]=t
TOK=re.compile(r'＠[^＠]*＠')
def wrap(en,ru):
    ru=ru.replace('\\n','\n')
    if '%' in en: return ru
    enw=max(len(x) for x in en.split('\n'))
    w=max(44,enw) if enw>30 else max(enw+4,22)
    if '\n' not in en.strip() and len(ru)<=(48 if enw>30 else w): return ru
    return '\n'.join(l for part in ru.split('\n') for l in (textwrap.wrap(part,w,break_long_words=False,break_on_hyphens=False) or ['']))
bad=0;m={}
for i,t in tr.items():
    en=src[i]
    if sorted(TOK.findall(en))!=sorted(TOK.findall(t)) or en.count('＋')!=t.count('＋') or sorted(re.findall(r'%[0-9]*[sd]',en))!=sorted(re.findall(r'%[0-9]*[sd]',t)) or en.count('%')!=t.count('%'):
        print('TOKEN MISMATCH',i,repr(en),repr(t)); bad+=1
    m[en]=wrap(en,t)
print('translated',len(tr),'of',len(src),'bad',bad)
cyr=re.compile('[А-Яа-яЁё]')
for f in sorted(glob.glob(S+'/in/*.xlsx')):
    wb=openpyxl.load_workbook(f); ws=wb.active; n=e=0
    for r in range(1,ws.max_row+1):
        a=ws.cell(r,1).value
        if a is None or (isinstance(a,str) and not a.strip()): continue
        if a in m: ws.cell(r,2).value=m[a]; n+=1
        elif not isinstance(a,str) or cyr.search(a) or not re.search('[A-Za-z]{3}',a): ws.cell(r,2).value=a; n+=1
        else: e+=1
    out=S+'/out/'+os.path.basename(f).replace('.eng_sdf.xlsx','.eng.rus.xlsx')
    wb.save(out); print(os.path.basename(out),'filled',n,'missing',e)
