"""Конвертер .eng <-> .txt в формате RF4STextExtractor (одна строка на запись, перенос строки = {LF}).

  python3 rf4s_txt.py export file.eng            -> file.eng.txt
  python3 rf4s_txt.py import original.eng file.txt out.eng
"""
import sys,struct
def read_eng(p):
    b=open(p,'rb').read(); n=struct.unpack('<I',b[4:8])[0]
    return b[:4],[b[o:o+l].decode('utf-8') if l else '' for l,o in (struct.unpack('<II',b[8+8*i:16+8*i]) for i in range(n))]
def write_eng(p,magic,strs):
    enc=[s.encode('utf-8') for s in strs]; n=len(enc)
    head=bytearray(magic)+struct.pack('<I',n); off=8+n*8; body=bytearray()
    for e in enc:
        if e: head+=struct.pack('<II',len(e),off); off+=len(e)+1; body+=e+b'\0'
        else: head+=struct.pack('<II',0,0); off+=1; body+=b'\0'   # пустая запись: длина 0, смещение 0, но байт NUL в теле есть
    open(p,'wb').write(bytes(head+body))
def read_txt(p):
    t=open(p,encoding='utf-8-sig',newline='').read().replace('\r\n','\n').split('\n')
    if t and t[-1]=='': t=t[:-1]
    return [x.replace('{LF}','\n') for x in t]
if __name__=='__main__':
    if sys.argv[1]=='export':
        m,s=read_eng(sys.argv[2])
        open(sys.argv[2]+'.txt','w',encoding='utf-8',newline='').write(''.join(x.replace('\n','{LF}')+'\r\n' for x in s))
    else:
        m,s=read_eng(sys.argv[2]); t=read_txt(sys.argv[3])
        assert len(s)==len(t),(len(s),len(t))
        write_eng(sys.argv[4],m,t)
