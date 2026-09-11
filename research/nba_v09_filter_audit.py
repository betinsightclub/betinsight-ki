import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip"
ZIP = Path('/tmp/basketball-final.sqlite.zip')
ROOT = Path('/tmp/nba_filter_audit')
DB = ROOT/'basketball-final.sqlite'
if not DB.exists():
    ROOT.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, ZIP)
    with zipfile.ZipFile(ZIP) as z: z.extractall(ROOT)

con = sqlite3.connect(DB)
odds = pd.read_sql_query('SELECT * FROM BettingOdds_History', con)
reg_ids = pd.read_sql_query('SELECT DISTINCT GAME_ID FROM Game_FullDetails', con)
con.close()

# Game_FullDetails is the regular-season detail table. Its intersection with odds gives the
# historical regular-season universe used by v0.9.
reg = odds[odds['GAME_ID'].isin(set(reg_ids['GAME_ID']))].copy()
print('ALL_ODDS', len(odds))
print('REGULAR_RAW', len(reg), 'TARGET', 17114)

core_cols = ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']
for c in core_cols + ['2H_HomeSpread','2H_Over']:
    reg[c] = pd.to_numeric(reg[c], errors='coerce')
core = reg.dropna(subset=core_cols).copy()
print('MODELABLE_OPEN_CLOSE', len(core), 'TARGET', 17113)
print('CORE_MISSING_ROWS')
print(reg[reg[core_cols].isna().any(axis=1)][['GAME_ID','Date','AwayTeam','HomeTeam']+core_cols+['2H_HomeSpread','2H_Over']].to_string(index=False))

# Test broad plausibility rules. We deliberately enumerate thresholds rather than assume one.
for spread_lim in [20,25,30,35,40,50,100]:
    for total_lo in [50,75,100,125,140,150]:
        mask = (
            core['HomeSpread_AtOpen'].abs().le(spread_lim) &
            core['HomeSpread_AtClose'].abs().le(spread_lim) &
            core['Over_AtOpen'].between(total_lo, 300) &
            core['Over_AtClose'].between(total_lo, 300)
        )
        n = int(mask.sum())
        if n in range(17090,17110) or n == 17099:
            h2n = int(core.loc[mask,'2H_HomeSpread'].notna().sum())
            both2h = int(core.loc[mask,['2H_HomeSpread','2H_Over']].notna().all(axis=1).sum())
            print('CANDIDATE', {'spread_lim':spread_lim,'total_lo':total_lo,'n':n,'h2spread_n':h2n,'both2h_n':both2h})

# Rank suspicious rows using very broad sanity boundaries.
susp = core[
    (core['HomeSpread_AtOpen'].abs()>30) |
    (core['HomeSpread_AtClose'].abs()>30) |
    (core['Over_AtOpen']<100) | (core['Over_AtOpen']>300) |
    (core['Over_AtClose']<100) | (core['Over_AtClose']>300)
].copy()
print('\nBROAD_SUSPICIOUS_COUNT', len(susp))
print(susp[['GAME_ID','Date','AwayTeam','HomeTeam']+core_cols+['2H_HomeSpread','2H_Over']].sort_values('Date').to_string(index=False))

# Show the tails, useful if the exact historical threshold was tighter.
print('\nLOWEST_OPEN_TOTALS')
print(core.nsmallest(25,'Over_AtOpen')[['GAME_ID','Date','AwayTeam','HomeTeam']+core_cols+['2H_HomeSpread','2H_Over']].to_string(index=False))
print('\nLOWEST_CLOSE_TOTALS')
print(core.nsmallest(25,'Over_AtClose')[['GAME_ID','Date','AwayTeam','HomeTeam']+core_cols+['2H_HomeSpread','2H_Over']].to_string(index=False))
print('\nLARGEST_ABS_SPREAD_ROWS')
t = core.assign(_mx=core[['HomeSpread_AtOpen','HomeSpread_AtClose']].abs().max(axis=1)).nlargest(30,'_mx')
print(t[['GAME_ID','Date','AwayTeam','HomeTeam']+core_cols+['2H_HomeSpread','2H_Over','_mx']].to_string(index=False))

# Candidate rule suggested by the workbook wording: normal NBA spread/total ranges.
for spread_lim,total_lo,total_hi in [(30,100,300),(40,100,300),(50,100,300),(30,125,300),(40,125,300),(50,125,300)]:
    m=(core['HomeSpread_AtOpen'].abs().le(spread_lim)&core['HomeSpread_AtClose'].abs().le(spread_lim)&
       core['Over_AtOpen'].between(total_lo,total_hi)&core['Over_AtClose'].between(total_lo,total_hi))
    clean=core[m]
    print('FINAL_CANDIDATE',spread_lim,total_lo,total_hi,'PLAUSIBLE',len(clean),'H2SPREAD',clean['2H_HomeSpread'].notna().sum(),'BOTH_H2',clean[['2H_HomeSpread','2H_Over']].notna().all(axis=1).sum())
