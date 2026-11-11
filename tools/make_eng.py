import struct,sys,openpyxl
def read_eng(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[4:8])[0]
    return b[:4],[b[o:o+l].decode('utf-8') for l,o in (struct.unpack('<II',b[8+8*i:16+8*i]) for i in range(n))],b
def recreate(magic,strs):
    enc=[s.encode('utf-8') for s in strs]; n=len(enc)
    head=bytearray(magic)+struct.pack('<I',n); off=8+n*8; body=bytearray()
    for e in enc:
        head+=struct.pack('<II',len(e),off); off+=len(e)+1; body+=e+b'\0'
    return bytes(head+body)

import re as _re
def fix_leftovers(orig,new):
    def tr(s):
        m=_re.fullmatch(r'Recommended [Ll]evel: (\d+)',s)
        if m: return 'Рекомендуемый уровень: '+m.group(1)
        m=_re.fullmatch(r'(Male|Female) Traveler (\d+)',s)
        if m: return ('Путешественник ' if m.group(1)=='Male' else 'Путешественница ')+m.group(2)
        m=_re.fullmatch(r'Opening (\d+)',s)
        if m: return 'Вступление '+m.group(1)
        return None
    n=0
    for i,x in enumerate(new):
        if _re.search('[A-Za-z]{4}',x) and not _re.search('[А-Яа-я]',x):
            t=tr(orig[i])
            if t: new[i]=t; n+=1
    return n

if __name__=='__main__':
    eng,xlsx,col,row,out=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),sys.argv[5]
    magic,strs,raw=read_eng(eng)
    assert recreate(magic,strs)==raw, 'roundtrip failed'
    ws=openpyxl.load_workbook(xlsx).active
    c=openpyxl.utils.column_index_from_string(col)
    new=[]
    for i in range(len(strs)):
        v=ws.cell(row+i,c).value
        if v is None or not str(v).strip():
            a=ws.cell(row+i,1).value
            v=a if a is not None and str(a).strip() else strs[i]
        new.append(str(v).replace('\r\n','\n'))
    print('fixed',fix_leftovers(strs,new))
    data=recreate(magic,new); open(out,'wb').write(data)
    m2,s2,_=read_eng(out); assert s2==new
    print('entries',len(new),'changed',sum(a!=b for a,b in zip(strs,new)),'empty',sum(1 for x in new if not x),'orig empty',sum(1 for x in strs if not x))
