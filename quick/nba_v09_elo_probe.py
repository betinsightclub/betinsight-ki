import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/elop.sqlite.zip'); R=Path('/tmp/elopdb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
DOM=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']
CT=np.array([-.8094746967645475,-.3325877729098592,-.27095763027679604,.24972916246690846,-.1656421906820333,.11024812552992498,.06462265416697556,-.04308359545971495])
con=sqlite3.connect(DB)
o=pd.read_sql_query('select * from BettingOdds_History',con)
d=pd.read_sql_query('select GAME_ID,TEAM_ABBREVIATION_HOME,TEAM_ABBREVIATION_AWAY,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con)
e1=pd.read_sql_query('select * from EloHistory',con);e2=pd.read_sql_query('select * from EloHistory_v2',con);con.close();d=d.drop_duplicates('GAME_ID')
r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)];r=r.dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)]
df=r.merge(d,on='GAME_ID',how='left',validate='many_to_one');q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy();df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s
htm=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);htt=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
actual=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));market=-df['2H_HomeSpread'];preg=-df.HomeSpread_AtClose;df['y']=actual-market
BASE=pd.DataFrame({'margin2h_vs_pregame_half':market-preg/2,'ht_margin':htm,'ht_margin_surprise':htm-preg/2,'spread_close':df.HomeSpread_AtClose,'total2h_vs_pregame_half':df['2H_Over']-df.Over_AtClose/2,'total_close':df.Over_AtClose,'total_move':df.Over_AtClose-df.Over_AtOpen,'ht_total_surprise':htt-df.Over_AtClose/2},index=df.index)

def elo_feature(e, same_day):
    x=e.copy();x['Date']=pd.to_datetime(x['Date']);x=x.set_index('Date').sort_index()
    vals=[];missing=[]
    for idx,row in df.iterrows():
        day=row.Date.normalize() if same_day else row.Date.normalize()-pd.Timedelta(days=1)
        # EloHistory is daily, but use latest available <= target day to survive gaps.
        p=x.loc[:day]
        if len(p)==0:
            vals.append(np.nan);missing.append((idx,'no_date',row.Date));continue
        snap=p.iloc[-1];h=str(row.TEAM_ABBREVIATION_HOME);a=str(row.TEAM_ABBREVIATION_AWAY)
        hv=snap[h] if h in snap.index else np.nan;av=snap[a] if a in snap.index else np.nan
        if pd.isna(hv) or pd.isna(av):missing.append((idx,h,a,row.Date,hv,av))
        vals.append(float(hv-av) if pd.notna(hv) and pd.notna(av) else np.nan)
    return pd.Series(vals,index=df.index),missing

def fit(X,tr,te,a):
    sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);B=sc.transform(X.loc[te.index]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B),m

def bs(c,y,g):
    k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def evaluate(name,X):
    good=X.notna().all(axis=1);dd=df[good].copy();X=X.loc[good]
    print('\n===',name,'ROWS',len(dd),'DROPPED',len(df)-len(dd),'===')
    alphaerr=0;z300=[]
    for a,tgt in TA.items():
        ds=[];zs=[]
        for s in DEV:
            te=dd[dd.season==s];tr=dd[dd.Date<pd.Timestamp(S[s][0])];c,_=fit(X,tr,te,a);b=np.sqrt(np.mean(te.y.to_numpy()**2));m=np.sqrt(np.mean((te.y.to_numpy()-c)**2));ds.append(b-m);zs.append(pd.DataFrame({'c':c,'y':te.y.to_numpy()}))
        st=(min(ds),float(np.mean(ds)),float(np.median(ds)));er=sum(abs(u-v) for u,v in zip(st,tgt));alphaerr+=er;print('ALPHA',a,'STATS',st,'TARGET',tgt,'ERR',er)
        if a==300:z300=zs
    z=pd.concat(z300,ignore_index=True);print('ALPHAERR',alphaerr);print('GATES')
    for g,t in TG.items():print(g,bs(z.c.to_numpy(),z.y.to_numpy(),g),'TARGET',t)
    print('OOS')
    for s,t in TO.items():
        te=dd[dd.season==s];tr=dd[dd.Date<pd.Timestamp(S[s][0])];c,_=fit(X,tr,te,300);rm=float(np.sqrt(np.mean((te.y.to_numpy()-c)**2)));b=bs(c,te.y.to_numpy(),.75);print(s,'N',len(te),'RMSE',repr(rm),'BETS',b,'TARGET',t)
    tr=dd[dd.season.isin(DEV)];sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);m=Ridge(alpha=300).fit(A,tr.y.to_numpy());coef=dict(zip(X.columns,m.coef_));cv=np.array([coef[x] for x in DOM]);print('DOM_COEFS',dict(zip(DOM,cv)));print('ELO_COEF',coef.get('elo_diff'));print('DOM_COEF_DIST',float(np.linalg.norm(cv-CT)))

# Base for reference.
evaluate('base8',BASE.copy())
for tab,e in [('elo1',e1),('elo2',e2)]:
    for sd in [False,True]:
        ef,miss=elo_feature(e,sd);print('\nELO_BUILD',tab,'same_day',sd,'missing',len(miss),'sample',miss[:10])
        X=BASE.copy();X['elo_diff']=ef;evaluate(tab+('_same' if sd else '_prior'),X)
