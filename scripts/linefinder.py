import os
path = os.path.join('c:','Users','augustoalmeida','Desktop','Ocorrências','app.py')
with open(path,'r',encoding='utf-8') as f:
    for i,l in enumerate(f,1):
        if '# IA' in l or 'if __name__' in l:
            print(i, l.strip())
