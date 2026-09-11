import math
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip"
ZIP = Path("/tmp/basketball-final.sqlite.zip")
DBDIR = Path("/tmp/nba_sqlite_exact")
DB = DBDIR / "basketball-final.sqlite"

TARGETS = {
    "2017-18": ("2017-10-17", "2018-04-11", 1230, 9.883179436414059),
    "2018-19": ("2018-10-16", "2019-04-10", 1230, 10.19949385002746),
    "2019-20": ("2019-10-22", "2020-08-14", None, 10.337244979978518),
    "2020-21": ("2020-12-22", "2021-05-16", None, 10.484913874395364),
}

if not DB.exists():
    DBDIR.mkdir(parents=True, exist_ok=True)
    print("DOWNLOAD", URL)
    urllib.request.urlretrieve(URL, ZIP)
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(DBDIR)
print("DB", DB, DB.stat().st_size)

con = sqlite3.connect(DB)

# Pull odds and detailed scores separately, deduping detailed records by GAME_ID.
odds = pd.read_sql_query('SELECT * FROM BettingOdds_History', con)
det = pd.read_sql_query('''
SELECT GAME_ID, GAME_DATE,
       PTS_QTR1_HOME, PTS_QTR2_HOME, PTS_QTR3_HOME, PTS_QTR4_HOME,
       PTS_OT1_HOME, PTS_OT2_HOME, PTS_OT3_HOME, PTS_OT4_HOME, PTS_OT5_HOME,
       PTS_HOME_y,
       PTS_QTR1_AWAY, PTS_QTR2_AWAY, PTS_QTR3_AWAY, PTS_QTR4_AWAY,
       PTS_OT1_AWAY, PTS_OT2_AWAY, PTS_OT3_AWAY, PTS_OT4_AWAY, PTS_OT5_AWAY
FROM Game_FullDetails
''', con)
con.close()
print("ODDS_ROWS", len(odds), "DETAIL_ROWS", len(det), "DETAIL_DUP_GAME_IDS", int(det.duplicated('GAME_ID').sum()))

det = det.drop_duplicates('GAME_ID', keep='first').copy()
# Legacy odds contain repeated placeholder GAME_ID='00'. The score side is unique after dedupe,
# so many-to-one is the correct validation and does not change any modern game row.
df = odds.merge(det, on='GAME_ID', how='left', validate='many_to_one')
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
for c in ['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_HOME_y',
          'PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY','2H_HomeSpread']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['ht_home_margin'] = (df['PTS_QTR1_HOME'] + df['PTS_QTR2_HOME']) - (df['PTS_QTR1_AWAY'] + df['PTS_QTR2_AWAY'])
ot_h = [f'PTS_OT{i}_HOME' for i in range(1,6)]
ot_a = [f'PTS_OT{i}_AWAY' for i in range(1,6)]
for c in ot_h + ot_a:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
df['calc_final_home'] = df[['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME'] + ot_h].sum(axis=1, min_count=4)
df['calc_final_away'] = df[['PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY'] + ot_a].sum(axis=1, min_count=4)
df['actual_2h_home_margin'] = (df['calc_final_home'] - df['calc_final_away']) - df['ht_home_margin']
df['expected_2h_home_margin'] = -pd.to_numeric(df['2H_HomeSpread'], errors='coerce')
df['baseline_error'] = df['actual_2h_home_margin'] - df['expected_2h_home_margin']

print("DATE_RANGE", df['Date'].min(), df['Date'].max())
print("JOIN_MISSING_Q1", int(df['PTS_QTR1_HOME'].isna().sum()))
print("2H_NON_NULL", int(df['2H_HomeSpread'].notna().sum()))

for label, (start, end, target_n, target_rmse) in TARGETS.items():
    s = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))].copy()
    modelable = s.dropna(subset=['actual_2h_home_margin','expected_2h_home_margin']).copy()
    r = float(np.sqrt(np.mean(np.square(modelable['baseline_error']))))
    print("\nSEASON", label)
    print("DATE_ROWS", len(s), "MODELABLE", len(modelable), "TARGET_N", target_n)
    print("BASELINE_RMSE", repr(r), "TARGET", repr(target_rmse), "ABS_DELTA", repr(abs(r-target_rmse)))
    print("SSE", repr(float(np.sum(np.square(modelable['baseline_error'])))))
    print("EXACT_RMSE_1E12", abs(r-target_rmse) < 1e-12)
    if label in {'2017-18','2018-19'}:
        london = modelable[modelable['Date'].isin([pd.Timestamp('2018-01-11'), pd.Timestamp('2019-01-17')])]
        if len(london):
            print("SPECIAL_DATE_ROWS")
            print(london[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','expected_2h_home_margin','actual_2h_home_margin','baseline_error']].to_string(index=False))

c = df[(df['Date'] >= pd.Timestamp('2017-10-17')) & (df['Date'] <= pd.Timestamp('2018-04-11'))].dropna(subset=['actual_2h_home_margin','expected_2h_home_margin']).copy()
c['flip_delta'] = 4*c['actual_2h_home_margin']*c['expected_2h_home_margin']
hits = c[np.isclose(c['flip_delta'], -12.0)]
print("\nSQLITE_SIGN_CANDIDATES_DELTA_MINUS12", len(hits))
print(hits[['GAME_ID','Date','AwayTeam','HomeTeam','2H_HomeSpread','expected_2h_home_margin','actual_2h_home_margin','flip_delta']].to_string(index=False))
