import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip"
ZIP = Path('/tmp/basketball-final.sqlite.zip')
ROOT = Path('/tmp/nba_clean_baseline')
DB = ROOT/'basketball-final.sqlite'
if not DB.exists():
    ROOT.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, ZIP)
    with zipfile.ZipFile(ZIP) as z: z.extractall(ROOT)

TARGETS = {
    '2017-18': ('2017-10-17','2018-04-11',1230,9.883179436414059),
    '2018-19': ('2018-10-16','2019-04-10',1230,10.19949385002746),
    '2019-20': ('2019-10-22','2020-08-14',None,10.337244979978518),
    '2020-21': ('2020-12-22','2021-05-16',None,10.484913874395364),
}

con=sqlite3.connect(DB)
odds=pd.read_sql_query('SELECT * FROM BettingOdds_History',con)
det=pd.read_sql_query('''
SELECT GAME_ID, GAME_DATE,
       PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,
       PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,
       PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,
       PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY
FROM Game_FullDetails
''',con)
con.close()
det=det.drop_duplicates('GAME_ID',keep='first')
reg=odds[odds['GAME_ID'].isin(set(det['GAME_ID']))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:
    reg[c]=pd.to_numeric(reg[c],errors='coerce')

# Reconstructed v0.9 cleaning chain.
clean=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']).copy()
clean=clean[
    clean['HomeSpread_AtOpen'].abs().le(30) &
    clean['HomeSpread_AtClose'].abs().le(30) &
    clean['Over_AtOpen'].between(100,300) &
    clean['Over_AtClose'].between(100,300)
].copy()
clean=clean.dropna(subset=['2H_HomeSpread','2H_Over']).copy()
clean=clean[clean['2H_Over'].between(50,200)].copy()
print('CLEAN_COUNT',len(clean),'TARGET 17090')

x=clean.merge(det,on='GAME_ID',how='left',validate='many_to_one')
score_cols=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME',
            'PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in score_cols:
    x[c]=pd.to_numeric(x[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):
        c=f'PTS_OT{i}_{side}'
        x[c]=pd.to_numeric(x[c],errors='coerce').fillna(0.0)
x=x.dropna(subset=score_cols).copy()
x['Date']=pd.to_datetime(x['Date'],errors='coerce')
x['ht_margin']=(x.PTS_QTR1_HOME+x.PTS_QTR2_HOME)-(x.PTS_QTR1_AWAY+x.PTS_QTR2_AWAY)
hcols=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME']+[f'PTS_OT{i}_HOME' for i in range(1,6)]
acols=['PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']+[f'PTS_OT{i}_AWAY' for i in range(1,6)]
x['final_home']=x[hcols].sum(axis=1)
x['final_away']=x[acols].sum(axis=1)
x['actual_2h_home_margin']=(x.final_home-x.final_away)-x.ht_margin
x['expected_2h_home_margin']=-x['2H_HomeSpread']
x['err']=x.actual_2h_home_margin-x.expected_2h_home_margin

for label,(start,end,target_n,target_rmse) in TARGETS.items():
    s=x[(x.Date>=pd.Timestamp(start))&(x.Date<=pd.Timestamp(end))].copy()
    rmse=float(np.sqrt(np.mean(np.square(s.err))))
    print('\nSEASON',label)
    print('N',len(s),'TARGET_N',target_n)
    print('RMSE',repr(rmse),'TARGET',repr(target_rmse),'ABS_DELTA',repr(abs(rmse-target_rmse)),'EXACT',abs(rmse-target_rmse)<1e-12)
    print('SSE',repr(float(np.sum(np.square(s.err)))))
