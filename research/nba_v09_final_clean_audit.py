import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip"
ZIP = Path('/tmp/basketball-final.sqlite.zip')
ROOT = Path('/tmp/nba_final_clean_audit')
DB = ROOT/'basketball-final.sqlite'
if not DB.exists():
    ROOT.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, ZIP)
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(ROOT)

con = sqlite3.connect(DB)
odds = pd.read_sql_query('SELECT * FROM BettingOdds_History', con)
det = pd.read_sql_query('''
SELECT GAME_ID, GAME_DATE,
       PTS_QTR1_HOME, PTS_QTR2_HOME, PTS_QTR3_HOME, PTS_QTR4_HOME,
       PTS_QTR1_AWAY, PTS_QTR2_AWAY, PTS_QTR3_AWAY, PTS_QTR4_AWAY,
       PTS_OT1_HOME, PTS_OT1_AWAY, PTS_HOME_y
FROM Game_FullDetails
''', con)
con.close()

det = det.drop_duplicates('GAME_ID', keep='first')
reg = odds[odds['GAME_ID'].isin(set(det['GAME_ID']))].copy()
numcols = ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']
for c in numcols:
    reg[c] = pd.to_numeric(reg[c], errors='coerce')

# Reproduce the already-confirmed historical chain: 17114 -> 17113 -> 17099.
modelable = reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']).copy()
plaus = modelable[
    modelable['HomeSpread_AtOpen'].abs().le(30) &
    modelable['HomeSpread_AtClose'].abs().le(30) &
    modelable['Over_AtOpen'].between(100,300) &
    modelable['Over_AtClose'].between(100,300)
].copy()
print('CHAIN', len(reg), len(modelable), len(plaus), 'TARGET 17114 17113 17099')

# Join score detail to inspect halftime/quarter completeness.
p = plaus.merge(det, on='GAME_ID', how='left', validate='many_to_one')
score_cols = ['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME',
              'PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in score_cols:
    p[c] = pd.to_numeric(p[c], errors='coerce')

missing_h2_spread = p[p['2H_HomeSpread'].isna()].copy()
missing_h2_total = p[p['2H_Over'].isna()].copy()
missing_any_score = p[p[score_cols].isna().any(axis=1)].copy()
missing_ht = p[p[['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY']].isna().any(axis=1)].copy()

print('MISSING_H2_SPREAD', len(missing_h2_spread))
print(missing_h2_spread[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over']].to_string(index=False))
print('\nMISSING_H2_TOTAL', len(missing_h2_total))
print(missing_h2_total[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over']].to_string(index=False))
print('\nMISSING_ANY_SCORE', len(missing_any_score))
print(missing_any_score[['GAME_ID','Date','AwayTeam','HomeTeam']+score_cols].to_string(index=False))
print('\nMISSING_HALFTIME', len(missing_ht))
print(missing_ht[['GAME_ID','Date','AwayTeam','HomeTeam','PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','2H_HomeSpread','2H_Over']].to_string(index=False))

# Inspect H2 plausibility tails after the pregame plausibility filter.
print('\nH2_SPREAD_EXTREMES')
print(p.assign(_abs2h=p['2H_HomeSpread'].abs()).nlargest(30,'_abs2h')[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over','_abs2h']].to_string(index=False))
print('\nH2_TOTAL_LOWEST')
print(p.nsmallest(30,'2H_Over')[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over']].to_string(index=False))
print('\nH2_TOTAL_HIGHEST')
print(p.nlargest(30,'2H_Over')[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over']].to_string(index=False))

# Enumerate sensible final-clean rules and only report counts near the historical 17090 target.
for spread_lim in [15,20,25,30,40,50]:
    for total_lo in [50,60,70,75,80]:
        for total_hi in [130,140,150,160,200]:
            m = (
                p['2H_HomeSpread'].notna() & p['2H_Over'].notna() &
                p['2H_HomeSpread'].abs().le(spread_lim) &
                p['2H_Over'].between(total_lo,total_hi) &
                p[['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY']].notna().all(axis=1)
            )
            n = int(m.sum())
            if 17086 <= n <= 17094:
                print('FINAL_RULE_CANDIDATE', {'spread_lim':spread_lim,'total_lo':total_lo,'total_hi':total_hi,'n':n})

# Also test the minimal rules separately to explain exactly where 17090 comes from.
base_h2 = p['2H_HomeSpread'].notna() & p['2H_Over'].notna()
print('\nCOUNTS_MINIMAL')
print('BOTH_H2', int(base_h2.sum()))
print('BOTH_H2_PLUS_HT', int((base_h2 & p[['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY']].notna().all(axis=1)).sum()))
print('BOTH_H2_PLUS_ALL_REG_SCORE', int((base_h2 & p[score_cols].notna().all(axis=1)).sum()))

# List every row excluded by the minimal final rule BOTH_H2 + halftime availability.
minimal = base_h2 & p[['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY']].notna().all(axis=1)
excluded = p.loc[~minimal, ['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','2H_Over','PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY']].copy()
print('\nEXCLUDED_MINIMAL', len(excluded))
print(excluded.sort_values('Date').to_string(index=False))
