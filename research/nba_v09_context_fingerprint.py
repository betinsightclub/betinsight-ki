import itertools
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL = "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip"
ZIP = Path('/tmp/basketball-final.sqlite.zip')
ROOT = Path('/tmp/nba_context_fingerprint')
DB = ROOT/'basketball-final.sqlite'
if not DB.exists():
    ROOT.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, ZIP)
    with zipfile.ZipFile(ZIP) as z: z.extractall(ROOT)

# Authoritative v0.9 fingerprints recovered from the workbook.
COEF_TARGET = np.array([
    -0.8094746967645475,
    -0.3325877729098592,
    -0.27095763027679604,
     0.24972916246690846,
    -0.1656421906820333,
     0.11024812552992498,
     0.06462265416697556,
    -0.04308359545971495,
])
FEATURES = [
    'margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close',
    'total2h_vs_pregame_half','total_close','total_move','ht_total_surprise'
]
OOS_TARGET = {
    '2017-18': {'rmse':9.858216869241469,'bets':332,'w':168,'l':157,'p':7},
    '2018-19': {'rmse':10.149329971984457,'bets':295,'w':155,'l':131,'p':9},
    '2019-20': {'rmse':10.288966913270224,'bets':246,'w':140,'l':101,'p':5},
    '2020-21': {'rmse':10.481849926111051,'bets':195,'w':99,'l':91,'p':5},
    '2021-22': {'rmse':10.767341369515634,'bets':89,'w':43,'l':44,'p':2},
}
DEV_TARGET = {'bets':664,'w':354,'l':293,'p':17,
              'worst':0.012949336036388814,'mean':0.02695917735504505,'median':0.025827748983386023}

SEASONS = {
    '2007-08':('2007-10-30','2008-04-16'),
    '2008-09':('2008-10-28','2009-04-15'),
    '2009-10':('2009-10-27','2010-04-14'),
    '2010-11':('2010-10-26','2011-04-13'),
    '2011-12':('2011-12-25','2012-04-26'),
    '2012-13':('2012-10-30','2013-04-17'),
    '2013-14':('2013-10-29','2014-04-16'),
    '2014-15':('2014-10-28','2015-04-15'),
    '2015-16':('2015-10-27','2016-04-13'),
    '2016-17':('2016-10-25','2017-04-12'),
    '2017-18':('2017-10-17','2018-04-11'),
    '2018-19':('2018-10-16','2019-04-10'),
    '2019-20':('2019-10-22','2020-08-14'),
    '2020-21':('2020-12-22','2021-05-16'),
    '2021-22':('2021-10-19','2021-12-20'),
}
DEV_SEASONS=['2013-14','2014-15','2015-16','2016-17']
OOS_SEASONS=['2017-18','2018-19','2019-20','2020-21','2021-22']

con=sqlite3.connect(DB)
odds=pd.read_sql_query('SELECT * FROM BettingOdds_History',con)
det=pd.read_sql_query('''
SELECT GAME_ID,
       PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,
       PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,
       PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,
       PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY
FROM Game_FullDetails
''',con)
con.close()
det=det.drop_duplicates('GAME_ID',keep='first')
reg=odds[odds.GAME_ID.isin(set(det.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:
    reg[c]=pd.to_numeric(reg[c],errors='coerce')
clean=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']).copy()
clean=clean[
    clean.HomeSpread_AtOpen.abs().le(30)&clean.HomeSpread_AtClose.abs().le(30)&
    clean.Over_AtOpen.between(100,300)&clean.Over_AtClose.between(100,300)
].copy()
clean=clean.dropna(subset=['2H_HomeSpread','2H_Over'])
clean=clean[clean['2H_Over'].between(50,200)].copy()
df=clean.merge(det,on='GAME_ID',how='left',validate='many_to_one')
score4=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in score4:
    df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):
        c=f'PTS_OT{i}_{side}'
        df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0.0)
df=df.dropna(subset=score4).copy()
df['Date']=pd.to_datetime(df['Date'])
df['season']='other'
for name,(start,end) in SEASONS.items():
    m=df.Date.between(pd.Timestamp(start),pd.Timestamp(end))
    df.loc[m,'season']=name

df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY)
df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
hcols=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME']+[f'PTS_OT{i}_HOME' for i in range(1,6)]
acols=['PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']+[f'PTS_OT{i}_AWAY' for i in range(1,6)]
df['final_margin']=df[hcols].sum(axis=1)-df[acols].sum(axis=1)
df['actual_2h_margin']=df.final_margin-df.ht_margin
df['market_2h_margin']=-df['2H_HomeSpread']
df['market_error']=df.actual_2h_margin-df.market_2h_margin

print('CLEAN',len(df),'SEASON_COUNTS',df[df.season!='other'].season.value_counts().sort_index().to_dict())

# Candidate feature definitions. These are deliberately small, interpretable sign alternatives,
# not a free-form optimization.
def make_features(base, m2_sign=1, spread_mode='raw', move_sign=1, surprise_sign=1, total2_sign=1):
    x=base.copy()
    preg_margin=-x.HomeSpread_AtClose
    preg_half_margin=preg_margin/2.0
    # Natural expected-margin difference; m2_sign=-1 gives raw-line-space difference.
    m2=(x.market_2h_margin-preg_half_margin)*m2_sign
    hts=(x.ht_margin-preg_half_margin)*surprise_sign
    spread=x.HomeSpread_AtClose if spread_mode=='raw' else preg_margin
    t2=(x['2H_Over']-x.Over_AtClose/2.0)*total2_sign
    move=(x.Over_AtClose-x.Over_AtOpen)*move_sign
    htt=(x.ht_total-x.Over_AtClose/2.0)*surprise_sign
    X=pd.DataFrame({
        'margin2h_vs_pregame_half':m2,
        'ht_margin':x.ht_margin,
        'ht_margin_surprise':hts,
        'spread_close':spread,
        'total2h_vs_pregame_half':t2,
        'total_close':x.Over_AtClose,
        'total_move':move,
        'ht_total_surprise':htt,
    },index=x.index)
    return X


def fit_predict(train,test,Xall,target_kind='residual',alpha=300):
    sc=StandardScaler()
    Xtr=sc.fit_transform(Xall.loc[train.index,FEATURES])
    Xte=sc.transform(Xall.loc[test.index,FEATURES])
    y=train.market_error.to_numpy() if target_kind=='residual' else train.actual_2h_margin.to_numpy()
    model=Ridge(alpha=alpha,fit_intercept=True)
    model.fit(Xtr,y)
    raw=model.predict(Xte)
    if target_kind=='residual':
        corr=raw
        pred_margin=test.market_2h_margin.to_numpy()+corr
    else:
        pred_margin=raw
        corr=pred_margin-test.market_2h_margin.to_numpy()
    return pred_margin,corr,model.coef_.copy(),model.intercept_,sc


def bets_from_corr(test,corr,gate=.75):
    corr=np.asarray(corr)
    edge=test.market_error.to_numpy()
    take=np.abs(corr)>=gate
    chosen_corr=corr[take]
    chosen_edge=edge[take]
    # Positive predicted correction -> home; negative -> away.
    signed_result=np.sign(chosen_corr)*chosen_edge
    w=int(np.sum(signed_result>1e-12)); l=int(np.sum(signed_result<-1e-12)); p=int(np.sum(np.abs(signed_result)<=1e-12))
    return int(take.sum()),w,l,p


def train_mask_for(test_season,mode):
    start=pd.Timestamp(SEASONS[test_season][0])
    if mode=='all_prior':
        return df.Date<start
    if mode=='from_2013':
        return (df.Date>=pd.Timestamp(SEASONS['2013-14'][0]))&(df.Date<start)
    if mode=='four_season':
        names=list(SEASONS)
        i=names.index(test_season)
        prev=names[max(0,i-4):i]
        return df.season.isin(prev)
    raise ValueError(mode)


def evaluate_variant(desc,Xall,target_kind,train_mode):
    # Development walk-forward folds.
    dev_rows=[]; all_dev_bets=[0,0,0,0]
    for s in DEV_SEASONS:
        te=df[df.season==s]
        tr=df[train_mask_for(s,train_mode)]
        if len(tr)<100: return None
        pred,corr,coef,inter,sc=fit_predict(tr,te,Xall,target_kind)
        base_rmse=float(np.sqrt(np.mean(np.square(te.market_error))))
        model_rmse=float(np.sqrt(np.mean(np.square(te.actual_2h_margin.to_numpy()-pred))))
        b=bets_from_corr(te,corr,.75)
        all_dev_bets=[a+v for a,v in zip(all_dev_bets,b)]
        dev_rows.append((s,base_rmse,model_rmse,base_rmse-model_rmse,b))
    deltas=np.array([r[3] for r in dev_rows])

    # OOS walk-forward.
    oos=[]
    rmse_abs=0.0; bet_abs=0
    for s in OOS_SEASONS:
        te=df[df.season==s]
        tr=df[train_mask_for(s,train_mode)]
        pred,corr,coef,inter,sc=fit_predict(tr,te,Xall,target_kind)
        mr=float(np.sqrt(np.mean(np.square(te.actual_2h_margin.to_numpy()-pred))))
        b=bets_from_corr(te,corr,.75)
        tgt=OOS_TARGET[s]
        rmse_abs+=abs(mr-tgt['rmse'])
        bet_abs+=abs(b[0]-tgt['bets'])+abs(b[1]-tgt['w'])+abs(b[2]-tgt['l'])+abs(b[3]-tgt['p'])
        oos.append((s,len(te),mr,b))

    # Compare coefficient vector under several plausible reporting fits.
    coeffits={}
    coef_specs={
        'pre2017_all': df.Date<pd.Timestamp(SEASONS['2017-18'][0]),
        'dev_only': df.season.isin(DEV_SEASONS),
        'through2020_21': df.Date<=pd.Timestamp(SEASONS['2020-21'][1]),
        'all_clean': np.ones(len(df),dtype=bool),
    }
    for name,mask in coef_specs.items():
        tr=df[mask]
        # Coefficients only; test can be any rows because fit_predict expects one.
        te=tr.iloc[:1]
        _,_,c,inter,sc=fit_predict(tr,te,Xall,target_kind)
        coeffits[name]=(float(np.linalg.norm(c-COEF_TARGET)),c)
    best_coef_name=min(coeffits,key=lambda k:coeffits[k][0])
    coef_dist,best_coef=coeffits[best_coef_name]

    devstat=(float(deltas.min()),float(deltas.mean()),float(np.median(deltas)))
    devstat_abs=sum(abs(a-b) for a,b in zip(devstat,(DEV_TARGET['worst'],DEV_TARGET['mean'],DEV_TARGET['median'])))
    devbet_abs=sum(abs(a-b) for a,b in zip(all_dev_bets,(DEV_TARGET['bets'],DEV_TARGET['w'],DEV_TARGET['l'],DEV_TARGET['p'])))
    score=rmse_abs*1000 + bet_abs*0.05 + devstat_abs*1000 + devbet_abs*0.05 + coef_dist*10
    return {
        'score':score,'desc':desc,'target':target_kind,'train_mode':train_mode,
        'dev_rows':dev_rows,'devstat':devstat,'devbets':tuple(all_dev_bets),
        'oos':oos,'rmse_abs':rmse_abs,'bet_abs':bet_abs,
        'coef_name':best_coef_name,'coef_dist':coef_dist,'coef':best_coef,'coeffits':coeffits,
    }

results=[]
for m2_sign,spread_mode,move_sign,surprise_sign,total2_sign,target_kind,train_mode in itertools.product(
    [1,-1],['raw','margin'],[1,-1],[1,-1],[1,-1],['residual','direct'],['all_prior','from_2013','four_season']):
    X=make_features(df,m2_sign,spread_mode,move_sign,surprise_sign,total2_sign)
    desc=f'm2={m2_sign},spread={spread_mode},move={move_sign},surp={surprise_sign},t2={total2_sign}'
    r=evaluate_variant(desc,X,target_kind,train_mode)
    if r is not None: results.append(r)

results.sort(key=lambda r:r['score'])
print('\nTOP_CANDIDATES')
for rank,r in enumerate(results[:12],1):
    print('\nRANK',rank,'SCORE',r['score'],r['desc'],'TARGET',r['target'],'TRAIN',r['train_mode'])
    print('DEVSTAT',r['devstat'],'TARGET',(DEV_TARGET['worst'],DEV_TARGET['mean'],DEV_TARGET['median']))
    print('DEVBETS',r['devbets'],'TARGET',(664,354,293,17))
    print('OOS',r['oos'])
    print('RMSE_ABS_SUM',r['rmse_abs'],'BET_ABS',r['bet_abs'])
    print('BEST_COEF_FIT',r['coef_name'],'DIST',r['coef_dist'])
    print('COEF',dict(zip(FEATURES,r['coef'])))
    print('COEF_TARGET',dict(zip(FEATURES,COEF_TARGET)))
    print('ALL_COEF_DIST', {k:v[0] for k,v in r['coeffits'].items()})

# A focused exact-check for the best candidate at all gate thresholds documented in Development.
best=results[0]
parts={k:v for k,v in [item.split('=') for item in best['desc'].split(',')]}
X=make_features(df,int(parts['m2']),parts['spread'],int(parts['move']),int(parts['surp']),int(parts['t2']))
print('\nBEST_DEV_GATE_TABLE')
for gate in [.25,.5,.75,1,1.25,1.5,2]:
    agg=[0,0,0,0]
    for s in DEV_SEASONS:
        te=df[df.season==s]; tr=df[train_mask_for(s,best['train_mode'])]
        pred,corr,coef,inter,sc=fit_predict(tr,te,X,best['target'])
        b=bets_from_corr(te,corr,gate)
        agg=[a+v for a,v in zip(agg,b)]
    print('GATE',gate,'RESULT',tuple(agg))
