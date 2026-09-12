import itertools, sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/smctx.sqlite.zip'); R=Path('/tmp/smctxdb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
DOM=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']

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
htm=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);htt=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
actual=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));market=-df['2H_HomeSpread'];preg=-df.HomeSpread_AtClose;df['y']=actual-market
F=pd.DataFrame(index=df.index)
F['margin2h_vs_pregame_half']=market-preg/2;F['ht_margin']=htm;F['ht_margin_surprise']=htm-preg/2;F['spread_close']=df.HomeSpread_AtClose;F['total2h_vs_pregame_half']=df['2H_Over']-df.Over_AtClose/2;F['total_close']=df.Over_AtClose;F['total_move']=df.Over_AtClose-df.Over_AtOpen;F['ht_total_surprise']=htt-df.Over_AtClose/2
# Anchor: strongest omitted candidate found so far.
F['spread_move']=df.HomeSpread_AtClose-df.HomeSpread_AtOpen
# Remaining pure-market / halftime-context candidates.
F['margin_remaining']=market-(preg-htm)
F['total_remaining']=df['2H_Over']-(df.Over_AtClose-htt)
F['market2h_margin']=market
F['h2_total']=df['2H_Over']
F['spread_open']=df.HomeSpread_AtOpen
F['total_open']=df.Over_AtOpen
F['ht_total']=htt
F['pregame_half_margin']=preg/2
F['pregame_half_total']=df.Over_AtClose/2
OPTIONAL=['margin_remaining','total_remaining','market2h_margin','h2_total','spread_open','total_open','ht_total','pregame_half_margin','pregame_half_total']
BASE=DOM+['spread_move']

def fit(cols,tr,te,a):
    sc=StandardScaler();A=sc.fit_transform(F.loc[tr.index,cols]);B=sc.transform(F.loc[te.index,cols]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B)
def bst(c,y,g):
    k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))
def eval300(cols):
    zs=[];ds=[]
    for s in DEV:
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c=fit(cols,tr,te,300);y=te.y.to_numpy();zs.append((c,y));ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))))
    c=np.concatenate([x for x,y in zs]);y=np.concatenate([y for x,y in zs]);st=(min(ds),float(np.mean(ds)),float(np.median(ds)));dserr=sum(abs(a-b) for a,b in zip(st,TA[300]));g={x:bst(c,y,x) for x in TG};gerr=sum(sum(abs(a-b) for a,b in zip(g[x],TG[x])) for x in TG)
    o=[];orm=obet=0
    for s,t in TO.items():
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];cc=fit(cols,tr,te,300);yy=te.y.to_numpy();rm=float(np.sqrt(np.mean((yy-cc)**2)));bb=bst(cc,yy,.75);o.append((s,rm,bb));orm+=abs(rm-t[0]);obet+=sum(abs(a-b) for a,b in zip(bb,t[1:]))
    # emphasize exact threshold fingerprint but require RMSE and seasonal stability too
    score=dserr*5000+gerr*.15+orm*2200+obet*.12
    return score,st,g,gerr,o,orm,obet

res=[]
for bits in itertools.product([0,1],repeat=len(OPTIONAL)):
    extras=[x for x,b in zip(OPTIONAL,bits) if b];cols=BASE+extras;z=eval300(cols);res.append((z[0],extras,z))
res.sort(key=lambda x:x[0])
print('CANDIDATES',len(res),'ANCHOR_ONLY_RANK',next(i+1 for i,x in enumerate(res) if not x[1]))
print('\nCLOSE_GATE75')
close=sorted(res,key=lambda x:(abs(x[2][2][.75][0]-664),sum(abs(a-b) for a,b in zip(x[2][2][.75],TG[.75])),x[0]))[:40]
for i,(sc,e,z) in enumerate(close,1):print(i,'SCORE',sc,'EXTRAS',e,'DEV',z[1],'G75',z[2][.75],'GERR',z[3],'OOS',z[4],'RMERR',z[5],'BETERR',z[6])
print('\nTOP_COMPOSITE')
for i,(sc,e,z) in enumerate(res[:30],1):print(i,'SCORE',sc,'EXTRAS',e,'DEV',z[1],'GATES',z[2],'OOS',z[4],'RMERR',z[5],'BETERR',z[6])

print('\nFULL_ALPHA_TOP15')
for i,(sc,e,z) in enumerate(res[:15],1):
    cols=BASE+e;ae=0;tab={}
    for a,t in TA.items():
        ds=[]
        for s in DEV:
            te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c=fit(cols,tr,te,a);y=te.y.to_numpy();ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))))
        st=(min(ds),float(np.mean(ds)),float(np.median(ds)));er=sum(abs(u-v) for u,v in zip(st,t));ae+=er;tab[a]=(st,er)
    print('\nRANK',i,'STAGE',sc,'EXTRAS',e,'ALPHAERR',ae);print('ALPHAS',tab);print('GATES',z[2]);print('OOS',z[4])
