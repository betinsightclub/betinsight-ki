import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/tmr.sqlite.zip'); R=Path('/tmp/tmrdb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)

S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
NAMES=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']
CT=np.array([-.8094746967645475,-.3325877729098592,-.27095763027679604,.24972916246690846,-.1656421906820333,.11024812552992498,.06462265416697556,-.04308359545971495])

con=sqlite3.connect(DB)
o=pd.read_sql_query('select * from BettingOdds_History',con)
d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con)
con.close();d=d.drop_duplicates('GAME_ID')
r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose'])
r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)]
r=r.dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)]
df=r.merge(d,on='GAME_ID',how='left',validate='many_to_one')
q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy();df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s
htm=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);htt=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
actual=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));market=-df['2H_HomeSpread'];preg=-df.HomeSpread_AtClose;df['y']=actual-market

BASE=pd.DataFrame({
'margin2h_vs_pregame_half':market-preg/2,
'ht_margin':htm,
'ht_margin_surprise':htm-preg/2,
'spread_close':df.HomeSpread_AtClose,
'total2h_vs_pregame_half':df['2H_Over']-df.Over_AtClose/2,
'total_close':df.Over_AtClose,
'total_move':df.Over_AtClose-df.Over_AtOpen,
'ht_total_surprise':htt-df.Over_AtClose/2},index=df.index)

MOVES={
'current_total_close_minus_open':df.Over_AtClose-df.Over_AtOpen,
'total_open_minus_close':df.Over_AtOpen-df.Over_AtClose,
'spread_close_minus_open':df.HomeSpread_AtClose-df.HomeSpread_AtOpen,
'spread_open_minus_close':df.HomeSpread_AtOpen-df.HomeSpread_AtClose,
'h2_vs_open_half':df['2H_Over']-df.Over_AtOpen/2,
'double_h2_vs_close':2*df['2H_Over']-df.Over_AtClose,
'halftime_total_reprice':df['2H_Over']+htt-df.Over_AtClose,
'halftime_total_reprice_inverse':df.Over_AtClose-df['2H_Over']-htt,
'h2_minus_firsthalf_actual':df['2H_Over']-htt,
'pregame_total_residual_after_ht':df.Over_AtClose-htt-df['2H_Over'],
}

def build(move_name):
    X=BASE.copy();X['total_move']=MOVES[move_name];return X

def fit(X,tr,te,a):
    sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);B=sc.transform(X.loc[te.index]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B),m,sc

def bstat(c,y,g):
    k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def dev_eval(X):
    alphaerr=0;atable={};dev300=[]
    for a,t in TA.items():
        ds=[];zs=[]
        for s in DEV:
            te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c,_,_=fit(X,tr,te,a);y=te.y.to_numpy();ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))));zs.append((c,y))
        st=(min(ds),float(np.mean(ds)),float(np.median(ds)));er=sum(abs(u-v) for u,v in zip(st,t));atable[a]=(st,er);alphaerr+=er
        if a==300:dev300=zs
    c=np.concatenate([a for a,b in dev300]);y=np.concatenate([b for a,b in dev300]);gates={g:bstat(c,y,g) for g in TG};gerr=sum(sum(abs(u-v) for u,v in zip(gates[g],TG[g])) for g in TG)
    return alphaerr,atable,gates,gerr

def oos_expanding(X):
    out=[];rmerr=berr=0
    for s,t in TO.items():
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c,_,_=fit(X,tr,te,300);y=te.y.to_numpy();rm=float(np.sqrt(np.mean((y-c)**2)));b=bstat(c,y,.75);out.append((s,rm,b));rmerr+=abs(rm-t[0]);berr+=sum(abs(u-v) for u,v in zip(b,t[1:]))
    return out,rmerr,berr

def oos_fixed_dev(X, train_mode):
    if train_mode=='pre2017_all': tr=df[df.Date<pd.Timestamp(S['2017-18'][0])]
    elif train_mode=='dev_only': tr=df[df.season.isin(DEV)]
    elif train_mode=='pre2013': tr=df[df.Date<pd.Timestamp(S['2013-14'][0])]
    else: raise ValueError(train_mode)
    sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);m=Ridge(alpha=300,fit_intercept=True).fit(A,tr.y.to_numpy())
    out=[];rmerr=berr=0
    for s,t in TO.items():
        te=df[df.season==s];c=m.predict(sc.transform(X.loc[te.index]));y=te.y.to_numpy();rm=float(np.sqrt(np.mean((y-c)**2)));b=bstat(c,y,.75);out.append((s,rm,b));rmerr+=abs(rm-t[0]);berr+=sum(abs(u-v) for u,v in zip(b,t[1:]))
    return out,rmerr,berr

results=[]
for mn in MOVES:
    X=build(mn);ae,at,g,ge=dev_eval(X);oe,ore,obe=oos_expanding(X)
    # coefficient fingerprint from development-only fit, with sign-oriented candidate as supplied
    tr=df[df.season.isin(DEV)];sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);m=Ridge(alpha=300).fit(A,tr.y.to_numpy());cd=float(np.linalg.norm(m.coef_-CT))
    score=ae*3000+ge*.12+ore*1800+obe*.10+cd*8
    results.append((score,mn,ae,at,g,ge,oe,ore,obe,m.coef_,cd))
results.sort()
print('RANKED MOVE REPLACEMENTS')
for rank,r in enumerate(results,1):
    score,mn,ae,at,g,ge,oe,ore,obe,coef,cd=r
    print('\nRANK',rank,'MOVE',mn,'SCORE',score,'ALPHAERR',ae,'GERR',ge,'RMERR',ore,'BETERR',obe,'COEFDIST',cd)
    print('ALPHAS',at);print('GATES',g);print('OOS_EXPANDING',oe);print('COEFS',dict(zip(NAMES,coef)))
    X=build(mn)
    for tm in ['pre2017_all','dev_only','pre2013']:
        fx,fre,fbe=oos_fixed_dev(X,tm);print('OOS_FIXED',tm,'RMERR',fre,'BETERR',fbe,fx)
