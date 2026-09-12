import sqlite3,urllib.request,zipfile
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip';Z=Path('/tmp/gate.zip');R=Path('/tmp/gatedb');DB=R/'basketball-final.sqlite'
if not DB.exists():
 R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z);zipfile.ZipFile(Z).extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')};DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID');r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)].dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)];df=r.merge(d,on='GAME_ID').copy();q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
 for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q);df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(a,b),'season']=s
hm=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME-df.PTS_QTR1_AWAY-df.PTS_QTR2_AWAY;ht=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY;act=df.PTS_QTR3_HOME+df.PTS_QTR4_HOME-df.PTS_QTR3_AWAY-df.PTS_QTR4_AWAY+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));market=-df['2H_HomeSpread'];preg=-df.HomeSpread_AtClose;df['y']=act-market
X=pd.DataFrame({'m2':market-preg/2,'hm':hm,'hs':hm-preg/2,'sc':df.HomeSpread_AtClose,'t2':df['2H_Over']-df.Over_AtClose/2,'tc':df.Over_AtClose,'tm':df.Over_AtClose-df.Over_AtOpen,'hts':ht-df.Over_AtClose/2},index=df.index)

def fitparts(s,N=None):
 te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];
 if N: tr=tr.tail(N)
 sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);B=sc.transform(X.loc[te.index]);m=Ridge(alpha=300,fit_intercept=True).fit(A,tr.y.to_numpy());full=m.predict(B);raw=B@m.coef_;return full,raw,te.y.to_numpy(),float(m.intercept_),float(tr.y.mean())
def stat(edge,side,y,g):
 k=np.abs(edge)>=g;r=np.sign(side[k])*y[k];return int(k.sum()),int((r>0).sum()),int((r<0).sum()),int((r==0).sum())

def sigs(full,raw,intercept):
 return {'full/full':(full,full),'raw/raw':(raw,raw),'raw/fullside':(raw,full),'full/rawside':(full,raw),'demean_test/demean_test':(full-full.mean(),full-full.mean()),'demean_test/fullside':(full-full.mean(),full),'full_minus_trainmean/rawside':(full-intercept,raw)}
for N in [None,12500]:
 print('\n========== N',N,'==========')
 cache={s:fitparts(s,N) for s in DEV+OOS}
 print('INTERCEPTS',[(s,cache[s][3],cache[s][4]) for s in DEV+OOS])
 names=list(sigs(*cache[DEV[0]][:2],cache[DEV[0]][3]).keys())
 for name in names:
  ee=[];ss=[];yy=[]
  for s in DEV:
   full,raw,y,it,mu=cache[s];e,side=sigs(full,raw,it)[name];ee.append(e);ss.append(side);yy.append(y)
  e=np.concatenate(ee);side=np.concatenate(ss);y=np.concatenate(yy);gates={g:stat(e,side,y,g) for g in TG};gerr=sum(sum(abs(a-b) for a,b in zip(gates[g],TG[g])) for g in TG)
  out=[];berr=0
  for s,t in TO.items():
   full,raw,y,it,mu=cache[s];edge,sd=sigs(full,raw,it)[name];b=stat(edge,sd,y,.75);berr+=sum(abs(a-bb) for a,bb in zip(b,t[1:]));out.append((s,b))
  print('\nMODE',name,'DEV_G75',gates[.75],'GERR',gerr,'BETERR',berr,'GATES',gates,'OOS',out)
 # sweep subtract c*intercept from full for gate+side and gate only
 print('\nINTERCEPT FRACTION SWEEP')
 rows=[]
 for c in np.arange(-1.0,2.001,.025):
  ee=[];ss=[];yy=[]
  for s in DEV:
   full,raw,y,it,mu=cache[s];z=full-c*it;ee.append(z);ss.append(z);yy.append(y)
  e=np.concatenate(ee);sd=np.concatenate(ss);y=np.concatenate(yy);gates={g:stat(e,sd,y,g) for g in TG};gerr=sum(sum(abs(a-b) for a,b in zip(gates[g],TG[g])) for g in TG);berr=0;oo=[]
  for s,t in TO.items():
   full,raw,y,it,mu=cache[s];z=full-c*it;b=stat(z,z,y,.75);berr+=sum(abs(a-bb) for a,bb in zip(b,t[1:]));oo.append((s,b))
  rows.append((gerr+berr,float(c),gerr,berr,gates,oo))
 for z in sorted(rows)[:15]:print('C',z[1],'TOTAL',z[0],'GERR',z[2],'BETERR',z[3],'G75',z[4][.75],'OOS',z[5])