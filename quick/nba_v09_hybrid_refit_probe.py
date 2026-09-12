import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/hybrid.sqlite.zip'); R=Path('/tmp/hybriddb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
CT=np.array([-.8094746967645475,-.3325877729098592,-.27095763027679604,.24972916246690846,-.1656421906820333,.11024812552992498,.06462265416697556,-.04308359545971495])
NAMES=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']

con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID')
r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)];r=r.dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)]
df=r.merge(d,on='GAME_ID',how='left',validate='many_to_one');q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy();df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s
htm=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);htt=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY;actual=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));market=-df['2H_HomeSpread'];preg=-df.HomeSpread_AtClose;df['y']=actual-market
X=pd.DataFrame({'margin2h_vs_pregame_half':market-preg/2,'ht_margin':htm,'ht_margin_surprise':htm-preg/2,'spread_close':df.HomeSpread_AtClose,'total2h_vs_pregame_half':df['2H_Over']-df.Over_AtClose/2,'total_close':df.Over_AtClose,'total_move':df.Over_AtClose-df.Over_AtOpen,'ht_total_surprise':htt-df.Over_AtClose/2},index=df.index)

def fit(tr,te,a=300):
    sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);B=sc.transform(X.loc[te.index]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B),m

def bstat(z,g):
    c=z.c.to_numpy();y=z.y.to_numpy();k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def pred_season(s,mode):
    teall=df[df.season==s].sort_values('Date').copy();outs=[]
    if mode=='season':
        tr=df[df.Date<pd.Timestamp(S[s][0])];c,_=fit(tr,teall);return pd.DataFrame({'c':c,'y':teall.y.to_numpy(),'date':teall.Date.to_numpy()})
    if mode=='month': keys=teall.Date.dt.to_period('M').astype(str)
    elif mode=='week_mon': keys=teall.Date.dt.to_period('W-SUN').astype(str)
    elif mode=='week_sun': keys=teall.Date.dt.to_period('W-SAT').astype(str)
    elif mode=='14d': keys=((teall.Date-pd.Timestamp(S[s][0])).dt.days//14).astype(str)
    elif mode=='21d': keys=((teall.Date-pd.Timestamp(S[s][0])).dt.days//21).astype(str)
    elif mode=='28d': keys=((teall.Date-pd.Timestamp(S[s][0])).dt.days//28).astype(str)
    elif mode=='daily': keys=teall.Date.dt.strftime('%Y-%m-%d')
    else: raise ValueError(mode)
    for k in keys.drop_duplicates():
        te=teall[keys==k];cut=te.Date.min();tr=df[df.Date<cut];c,_=fit(tr,te);outs.append(pd.DataFrame({'c':c,'y':te.y.to_numpy(),'date':te.Date.to_numpy()}))
    return pd.concat(outs,ignore_index=True)

for mode in ['season','month','week_mon','week_sun','14d','21d','28d','daily']:
    print('\n===',mode,'===')
    dev=pd.concat([pred_season(s,mode) for s in DEV],ignore_index=True)
    print('GATES')
    for g,t in TG.items():print(g,bstat(dev,g),'TARGET',t)
    print('OOS')
    rmerr=0;berr=0
    for s,t in TO.items():
        z=pred_season(s,mode);rm=float(np.sqrt(np.mean((z.y.to_numpy()-z.c.to_numpy())**2)));bs=bstat(z,.75);rmerr+=abs(rm-t[0]);berr+=sum(abs(a-b) for a,b in zip(bs,t[1:]));print(s,'RMSE',repr(rm),'BETS',bs,'TARGET',t)
    print('OOS_ERR',rmerr,berr)

print('\n=== COEFFICIENT SOURCE PROBE ===')
trainsets={
'pre2013':df[df.Date<pd.Timestamp(S['2013-14'][0])],
'dev_only':df[df.season.isin(DEV)],
'pre2017_all':df[df.Date<pd.Timestamp(S['2017-18'][0])],
}
for tn,tr in trainsets.items():
    for a in [100,300,500,750,1000,1500,2000]:
        sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());dist=float(np.linalg.norm(m.coef_-CT));print(tn,'alpha',a,'N',len(tr),'DIST',dist,'COEFS',dict(zip(NAMES,m.coef_)))
