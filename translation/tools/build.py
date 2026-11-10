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
    if '\n' in ru or '\n' not in en: return ru
    w=max(28,max(len(x) for x in en.split('\n')))
    return '\n'.join(textwrap.wrap(ru,w,break_long_words=False,break_on_hyphens=False))
bad=0;m={}
for i,t in tr.items():
    en=src[i]
    if sorted(TOK.findall(en))!=sorted(TOK.findall(t)) or en.count('＋')!=t.count('＋'):
        print('TOKEN MISMATCH',i,repr(en),repr(t)); bad+=1
    m[en]=wrap(en,t)
print('translated',len(tr),'of',len(src),'bad',bad)
wb=openpyxl.load_workbook(S+'/in/src.xlsx'); ws=wb.active; n=0
for row in ws.iter_rows(min_row=2,max_col=2):
    a,b=row[0].value,row[1].value
    if isinstance(a,str) and b==a and a in m: row[1].value=m[a]; n+=1
wb.save(S+'/rf3mc.eng.rus.xlsx'); print('cells filled',n)
