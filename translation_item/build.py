import openpyxl,re,json,sys,glob,textwrap
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
    if '\n' not in en.strip(): return ru
    w=max(40,max(len(x) for x in en.split('\n')))
    return '\n'.join(l for part in ru.split('\n') for l in (textwrap.wrap(part,w,break_long_words=False,break_on_hyphens=False) or ['']))
bad=0;m={}
for i,t in tr.items():
    en=src[i]
    if sorted(TOK.findall(en))!=sorted(TOK.findall(t)) or en.count('＋')!=t.count('＋'):
        print('TOKEN MISMATCH',i,repr(en),repr(t)); bad+=1
    m[en]=wrap(en,t)
print('translated',len(tr),'of',len(src),'bad',bad)
cyr=re.compile('[А-Яа-яЁё]')
wb=openpyxl.load_workbook(S+'/in/src.xlsx'); ws=wb.active; n=0
ws.cell(1,2).value=ws.cell(1,2).value
for r in range(1,ws.max_row+1):
    a=ws.cell(r,1).value
    if not isinstance(a,str) or not a.strip(): continue
    if a in m: ws.cell(r,2).value=m[a]; n+=1
    elif cyr.search(a) or not re.search('[A-Za-z]{3}',a): ws.cell(r,2).value=a; n+=1
wb.save(S+'/rf3TxtItem_split2_2.eng.rus.xlsx'); print('cells filled',n)
