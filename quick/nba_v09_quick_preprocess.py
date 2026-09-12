import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'; Z=Path('/tmp/b.sqlite.zip'); R=Path('/tmp/bq'); DB=R/'basketball-final.sqlite'
if not DB.exists():
 R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
 with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TR={'2017-18':9.858216869241469,'2018-19':10.149329971984457,'2019-20':10.288966913270224,'2020-21':10.481849926111051,'2021-22':10.767341369515634};TB={'2017-18':332,'2018-19':295,'2019-20':246,'2020-21':195,'2021-22':89}
con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID')
reg=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:reg[c]=pd.to_numeric(reg[c],errors='coerce')
reg=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);reg=reg[reg.HomeSpread_AtOpen.abs().le(30)&reg.HomeSpread_AtClose.abs().le(30)&reg.Over_AtOpen.between(100,300)&reg.Over_AtClose.between(100,300)];reg=reg.dropna(subset=['2H_HomeSpread','2H_Over']);reg=reg[reg['2H_Over'].between(50,200)]
df=reg.merge(d,on='GAME_ID',how='left');q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for x in ['HOME','AWAY']:
 for i in range(1,6):df[f'PTS_OT{i}_{x}']=pd.to_numeric(df[f'PTS_OT{i}_{x}'],errors='coerce').fillna(0)
df=df.dropna(subset=q);df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(a,b),'season']=s
df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY;df['reg2h']=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY);df['otm']=sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));df['actual']=df.reg2h+df.otm;df['market']=-df['2H_HomeSpread'];df['yot']=df.actual-df.market;df['yreg']=df.reg2h-df.market
preg=-df.HomeSpread_AtClose;X=pd.DataFrame({'m2':df.market-preg/2,'ht':df.ht_margin,'hts':df.ht_margin-preg/2,'sp':df.HomeSpread_AtClose,'t2':df['2H_Over']-df.Over_AtClose/2,'tc':df.Over_AtClose,'tm':df.Over_AtClose-df.Over_AtOpen,'htt':df.ht_total-df.Over_AtClose/2},index=df.index)

def go(mode,inter,target):
 dev=[];db=0;oos=[]
 for s in DEV+OOS:
  te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];A=X.loc[tr.index].to_numpy();B=X.loc[te.index].to_numpy()
  if mode=='std':sc=StandardScaler();A=sc.fit_transform(A);B=sc.transform(B)
  elif mode=='raw':pass
  elif mode=='global':sc=StandardScaler().fit(X);A=sc.transform(A);B=sc.transform(B)
  m=Ridge(alpha=300,fit_intercept=inter).fit(A,tr[target]);corr=m.predict(B);pred=te.market.to_numpy()+corr;rm=float(np.sqrt(np.mean((te.actual.to_numpy()-pred)**2)));bets=int((np.abs(corr)>=.75).sum())
  if s in DEV:dev.append((s,rm,bets));db+=bets
  else:oos.append((s,rm,bets,TR[s],TB[s]))
 print('\n',mode,inter,target,'DEV_BETS',db,'OOS',oos,'DEV',dev)
for mode in ['std','raw','global']:
 for inter in [True,False]:
  for target in ['yot','yreg']:go(mode,inter,target)
