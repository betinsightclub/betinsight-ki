import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/mwf.sqlite.zip'); R=Path('/tmp/mwfdb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z: z.extractall(R)

SEASONS={
'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),
'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),
'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),
'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),
'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
ALPHA_TARGET={
10:(0.009858199953276525,0.03022947944542187,0.03099032558293935),
30:(0.010448690894154566,0.0300874616301412,0.030785955809568222),
100:(0.01181166035632586,0.029377116254404978,0.02939163151319235),
300:(0.012949336036388814,0.02695917735504505,0.025827748983386023),
1000:(0.011899062924864978,0.021358065322965913,0.01913939031452916)}
GATE_TARGET={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
OOS_TARGET={
'2017-18':(9.858216869241469,332,168,157,7),
'2018-19':(10.149329971984457,295,155,131,9),
'2019-20':(10.288966913270224,246,140,101,5),
'2020-21':(10.481849926111051,195,99,91,5),
'2021-22':(10.767341369515634,89,43,44,2)}

con=sqlite3.connect(DB)
o=pd.read_sql_query('select * from BettingOdds_History',con)
d=pd.read_sql_query('''select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails''',con)
con.close(); d=d.drop_duplicates('GAME_ID')
reg=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']: reg[c]=pd.to_numeric(reg[c],errors='coerce')
reg=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose'])
reg=reg[reg.HomeSpread_AtOpen.abs().le(30)&reg.HomeSpread_AtClose.abs().le(30)&reg.Over_AtOpen.between(100,300)&reg.Over_AtClose.between(100,300)]
reg=reg.dropna(subset=['2H_HomeSpread','2H_Over']); reg=reg[reg['2H_Over'].between(50,200)]
df=reg.merge(d,on='GAME_ID',how='left',validate='many_to_one')
q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q: df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6): df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy(); df.Date=pd.to_datetime(df.Date); df['season']='other'
for s,(a,b) in SEASONS.items(): df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s

df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY)
df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
df['actual']=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6))
df['market']=-df['2H_HomeSpread']; df['y']=df.actual-df.market
preg=-df.HomeSpread_AtClose
X=pd.DataFrame({
'margin2h_vs_pregame_half':df.market-preg/2,
'ht_margin':df.ht_margin,
'ht_margin_surprise':df.ht_margin-preg/2,
'spread_close':df.HomeSpread_AtClose,
'total2h_vs_pregame_half':df['2H_Over']-df.Over_AtClose/2,
'total_close':df.Over_AtClose,
'total_move':df.Over_AtClose-df.Over_AtOpen,
'ht_total_surprise':df.ht_total-df.Over_AtClose/2},index=df.index)

def fit_predict(train,test,alpha):
    sc=StandardScaler(); A=sc.fit_transform(X.loc[train.index]); B=sc.transform(X.loc[test.index])
    m=Ridge(alpha=alpha,fit_intercept=True).fit(A,train.y.to_numpy())
    return m.predict(B)

def group_period(series,kind):
    if kind=='month': return series.dt.to_period('M').astype(str)
    if kind=='week': return series.dt.to_period('W-SUN').astype(str)
    if kind=='quarter': return series.dt.to_period('Q').astype(str)
    raise ValueError(kind)

def walk_predictions(rows,alpha,kind,start_train=None):
    rows=rows.sort_values('Date').copy(); groups=group_period(rows.Date,kind)
    out=[]
    for g in groups.drop_duplicates():
        te=rows[groups==g]
        cutoff=te.Date.min()
        tr=df[df.Date<cutoff]
        if start_train is not None: tr=tr[tr.Date>=pd.Timestamp(start_train)]
        if len(tr)<100: continue
        c=fit_predict(tr,te,alpha)
        out.append(pd.DataFrame({'idx':te.index,'corr':c,'group':g,'y':te.y.to_numpy(),'actual':te.actual.to_numpy(),'market':te.market.to_numpy(),'season':te.season.to_numpy()}))
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def rmse_delta_by_group(pred):
    vals=[]
    for g,z in pred.groupby('group'):
        b=float(np.sqrt(np.mean(z.y.to_numpy()**2)))
        m=float(np.sqrt(np.mean((z.y.to_numpy()-z.corr.to_numpy())**2)))
        vals.append((g,len(z),b-m,b,m))
    d=np.array([x[2] for x in vals])
    return (float(d.min()),float(d.mean()),float(np.median(d))),vals

def bet_stats(pred,gate):
    z=pred[np.abs(pred.corr)>=gate]
    r=np.sign(z.corr.to_numpy())*z.y.to_numpy()
    return (len(z),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def eval_kind(kind,start_train=None):
    devrows=df[df.season.isin(DEV)].copy(); oosrows=df[df.season.isin(OOS)].copy()
    print('\n===',kind,'START',start_train,'===')
    alpha_err=0
    for a,tgt in ALPHA_TARGET.items():
        p=walk_predictions(devrows,a,kind,start_train); stats,vals=rmse_delta_by_group(p)
        e=sum(abs(x-y) for x,y in zip(stats,tgt)); alpha_err+=e
        print('ALPHA',a,'N_GROUPS',len(vals),'STATS',stats,'TARGET',tgt,'ERR',e)
        if a==300:
            print('A300_GROUP_DELTAS',vals)
            print('A300_GATE_TABLE')
            for g,t in GATE_TARGET.items(): print(g,bet_stats(p,g),'TARGET',t)
    print('ALPHA_ERR_SUM',alpha_err)
    po=walk_predictions(oosrows,300,kind,start_train)
    print('OOS_MONTHLY/REFIT')
    for s,t in OOS_TARGET.items():
        z=po[po.season==s]
        rm=float(np.sqrt(np.mean((z.y.to_numpy()-z.corr.to_numpy())**2)))
        b=bet_stats(z,.75)
        print(s,'N',len(z),'RMSE',repr(rm),'BETS',b,'TARGET',t)

for kind in ['month','quarter','week']:
    eval_kind(kind,None)
# Monthly with the two historically plausible starts most worth fingerprinting.
for st in ['2008-10-28','2010-10-26']:
    eval_kind('month',st)
