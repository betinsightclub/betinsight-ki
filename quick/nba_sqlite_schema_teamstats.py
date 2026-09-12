import sqlite3, urllib.request, zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/schema.sqlite.zip');R=Path('/tmp/schemadb');DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
con=sqlite3.connect(DB)
tabs=[x[0] for x in con.execute("select name from sqlite_master where type='table' order by name")]
print('TABLES',tabs)
for t in tabs:
    cols=[r[1] for r in con.execute(f'pragma table_info("{t}")')]
    low=' '.join(cols).lower()
    if t in ['Game','Game_FullDetails','Game_Playoffs'] or any(k in low for k in ['offensive','rating','pace','rebound','turnover','field_goal','fg_pct','ast','reb','poss']):
        print('\nTABLE',t,'N_COLS',len(cols),'COUNT',con.execute(f'select count(*) from "{t}"').fetchone()[0])
        print('COLUMNS')
        for i,c in enumerate(cols):print(i,c)
con.close()
