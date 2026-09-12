import sqlite3, urllib.request, zipfile
from pathlib import Path
URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/schema.sqlite.zip');R=Path('/tmp/schemadb');DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
con=sqlite3.connect(DB)
for t in ['EloHistory','EloHistory_v2','Team']:
    cols=[r[1] for r in con.execute(f'pragma table_info("{t}")')]
    print('\nTABLE',t,'N_COLS',len(cols),'COUNT',con.execute(f'select count(*) from "{t}"').fetchone()[0])
    print('COLUMNS',cols)
    print('FIRST5')
    for row in con.execute(f'select * from "{t}" limit 5'): print(row)
    print('LAST5')
    order_candidates=[c for c in cols if any(x in c.lower() for x in ['date','game_id','id'])]
    if order_candidates:
        oc=order_candidates[0]
        try:
            for row in con.execute(f'select * from "{t}" order by "{oc}" desc limit 5'): print(row)
        except Exception as e: print('ORDER_ERR',repr(e))
    else:
        for row in con.execute(f'select * from "{t}" limit 5'): print(row)
    # Show uniqueness/key diagnostics for likely join columns.
    for c in cols:
        if c.lower() in ['game_id','team_id','team','date','game_date','game_date_est']:
            try:
                n=con.execute(f'select count(distinct "{c}") from "{t}"').fetchone()[0]
                print('DISTINCT',c,n)
            except Exception as e: print('DISTINCT_ERR',c,repr(e))
con.close()
