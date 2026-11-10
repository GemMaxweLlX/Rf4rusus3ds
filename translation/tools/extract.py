import openpyxl,re,json,sys
S=sys.argv[1]
wb=openpyxl.load_workbook(S+'/in/src.xlsx',)
ws=wb.active
seen={};order=[]
for r in ws.iter_rows(min_row=2,values_only=True):
    r=tuple(r)+(None,None); a,b=r[0],r[1]
    if not isinstance(a,str): continue
    if re.search('[А-Яа-яЁё]',a) or not re.search('[A-Za-z]',a): continue
    if b!=a: continue
    if a not in seen: seen[a]=len(order); order.append(a)
json.dump(order,open(S+'/tr/src.json','w'),ensure_ascii=False)
print(len(order))
