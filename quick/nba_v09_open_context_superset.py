import itertools,sqlite3,urllib.request,zipfile
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip';Z=Path('/tmp/openctx.zip');R=Path('/tmp/openctx');DB=R/'basketball-final.sqlite'
if not DB.exists():
 R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z);zipfile.ZipFile(Z).extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')};DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID');r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)].dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)];df=r.merge(d,on='GAME_ID').copy();q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
 for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q);df.Date=pd.to_datetime(df.Date);df=df.sort_values(['Date','GAME_ID']).reset_index(drop=True);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(a,b),'season']=s
hm=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME-df.PTS_QTR1_AWAY-df.PTS_QTR2_AWAY;ht=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY;act=df.PTS_QTR3_HOME+df.PTS_QTR4_HOME-df.PTS_QTR3_AWAY-df.PTS_QTR4_AWAY+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));m=-df['2H_HomeSpread'];pc=-df.HomeSpread_AtClose;po=-df.HomeSpread_AtOpen;tc=df.Over_AtClose;to=df.Over_AtOpen;df['y']=act-m
X=pd.DataFrame({'m2_close':m-pc/2,'hm':hm,'hs_close':hm-pc/2,'spread_close':df.HomeSpread_AtClose,'t2_close':df['2H_Over']-tc/2,'total_close':tc,'total_move':tc-to,'hts_close':ht-tc/2,'m2_open':m-po/2,'hs_open':hm-po/2,'t2_open':df['2H_Over']-to/2,'hts_open':ht-to/2,'spread_move':df.HomeSpread_AtClose-df.HomeSpread_AtOpen,'spread_open':df.HomeSpread_AtOpen,'total_open':to},index=df.index)
BASE=['m2_close','hm','hs_close','spread_close','t2_close','total_close','total_move','hts_close'];OPT=['m2_open','hs_open','t2_open','hts_open','spread_move','spread_open','total_open']
def fit(cols,s,a=300,N=None):
 te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];
 if N:tr=tr.tail(N)
 sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index,cols]);B=sc.transform(X.loc[te.index,cols]);return Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy()).predict(B),te.y.to_numpy()
def bs(c,y,g):
 k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return int(k.sum()),int((r>0).sum()),int((r<0).sum()),int((r==0).sum())
def eval300(cols,N=None):
 dev=[];ds=[]
 for s in DEV:
  c,y=fit(cols,s,300,N);dev.append((c,y));ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))))
 c=np.concatenate([z[0] for z in dev]);y=np.concatenate([z[1] for z in dev]);st=(min(ds),float(np.mean(ds)),float(np.median(ds)));g={v:bs(c,y,v) for v in TG};de=sum(abs(a-b) for a,b in zip(st,TA[300]));ge=sum(sum(abs(a-b) for a,b in zip(g[v],TG[v])) for v in TG);oo=[];re=be=0
 for s,t in TO.items():
  c,y=fit(cols,s,300,N);rm=float(np.sqrt(np.mean((y-c)**2)));b=bs(c,y,.75);oo.append((s,rm,b));re+=abs(rm-t[0]);be+=sum(abs(a-bb) for a,bb in zip(b,t[1:]))
 score=de*5000+ge*.12+re*2500+be*.12;return score,st,g,ge,oo,re,be
res=[]
for bits in itertools.product([0,1],repeat=len(OPT)):
 ex=[f for f,b in zip(OPT,bits) if b];z=eval300(BASE+ex);res.append((z[0],ex,z))
res.sort(key=lambda r:r[0]);print('CANDIDATES',len(res),'BASE_RANK',next(i+1 for i,r in enumerate(res) if not r[1]))
print('TOP40')
for i,(sc,e,z) in enumerate(res[:40],1):print(i,'SCORE',sc,'EXTRAS',e,'DEV',z[1],'G75',z[2][.75],'GERR',z[3],'RMERR',z[5],'BETERR',z[6],'OOS',z[4])
print('\nCLOSEST G75')
for i,(sc,e,z) in enumerate(sorted(res,key=lambda r:(abs(r[2][2][.75][0]-664),sum(abs(a-b) for a,b in zip(r[2][2][.75],TG[.75])),r[0]))[:25],1):print(i,'SCORE',sc,'EXTRAS',e,'DEV',z[1],'GATES',z[2],'OOS',z[4])
print('\nFULL_ALPHA_AND_CAP12500 TOP20')
for rank,(sc,e,z) in enumerate(res[:20],1):
 cols=BASE+e;ae=0;tab={}
 for a,t in TA.items():
  ds=[]
  for s in DEV:
   c,y=fit(cols,s,a);ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))))
  st=(min(ds),float(np.mean(ds)),float(np.median(ds)));er=sum(abs(u-v) for u,v in zip(st,t));ae+=er;tab[a]=(st,er)
 cap=eval300(cols,12500)
 print('\nRANK',rank,'EXTRAS',e,'STAGE',sc,'ALPHAERR',ae,'ALPHAS',tab);print('EXP_GATES',z[2],'EXP_OOS',z[4]);print('CAP12500_GATES',cap[2],'CAP12500_OOS',cap[4],'CAP_SCORE',cap[0])