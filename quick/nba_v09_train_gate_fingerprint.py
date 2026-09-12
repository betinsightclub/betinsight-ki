import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip';Z=Path('/tmp/tg.sqlite.zip');R=Path('/tmp/tgdb');DB=R/'basketball-final.sqlite'
if not DB.exists():
 R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
 with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
ALPHAS=[10,30,100,300,1000]
TSEL={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TOOS={'2017-18':(9.858216869241469,332),'2018-19':(10.149329971984457,295),'2019-20':(10.288966913270224,246),'2020-21':(10.481849926111051,195),'2021-22':(10.767341369515634,89)}
T_GATE={.25:2841,.5:1419,.75:664,1:302,1.25:129,1.5:50,2:12}
DEV4=['2013-14','2014-15','2015-16','2016-17'];DEV3=['2014-15','2015-16','2016-17'];OOS=list(TOOS)
con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID')
reg=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:reg[c]=pd.to_numeric(reg[c],errors='coerce')
reg=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);reg=reg[reg.HomeSpread_AtOpen.abs().le(30)&reg.HomeSpread_AtClose.abs().le(30)&reg.Over_AtOpen.between(100,300)&reg.Over_AtClose.between(100,300)];reg=reg.dropna(subset=['2H_HomeSpread','2H_Over']);reg=reg[reg['2H_Over'].between(50,200)]
df=reg.merge(d,on='GAME_ID',how='left');q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
 for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q);df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(a,b),'season']=s
df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY;df['actual']=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));df['market']=-df['2H_HomeSpread'];df['y']=df.actual-df.market
preg=-df.HomeSpread_AtClose
X=pd.DataFrame({'m2':df.market-preg/2,'ht':df.ht_margin,'hts':df.ht_margin-preg/2,'sp':df.HomeSpread_AtClose,'t2':df['2H_Over']-df.Over_AtClose/2,'tc':df.Over_AtClose,'tm':df.Over_AtClose-df.Over_AtOpen,'htt':df.ht_total-df.Over_AtClose/2},index=df.index)

def predict(train,test,alpha=300):
 sc=StandardScaler();A=sc.fit_transform(X.loc[train.index]);B=sc.transform(X.loc[test.index]);m=Ridge(alpha=alpha).fit(A,train.y);return m.predict(B)
def fold_deltas(start,folds,alpha):
 vals=[]
 for s in folds:
  te=df[df.season==s];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S[s][0]))]
  if len(tr)<100:return None
  c=predict(tr,te,alpha);base=np.sqrt(np.mean(te.y**2));model=np.sqrt(np.mean((te.y.to_numpy()-c)**2));vals.append(base-model)
 return (min(vals),float(np.mean(vals)),float(np.median(vals))),vals
def oos_score(start):
 rows=[];err=0
 for s,(trm,tb) in TOOS.items():
  te=df[df.season==s];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S[s][0]))];c=predict(tr,te,300);rm=np.sqrt(np.mean((te.y.to_numpy()-c)**2));b=int((np.abs(c)>=.75).sum());err+=abs(rm-trm)*1000+abs(b-tb)*.05;rows.append((s,round(rm,12),b))
 return err,rows
def gate_counts(start,mode):
 pred=[];tes=[]
 if mode=='oof4':
  for s in DEV4:
   te=df[df.season==s];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S[s][0]))];pred.append(predict(tr,te));tes.append(te)
 elif mode=='oof3':
  for s in DEV3:
   te=df[df.season==s];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S[s][0]))];pred.append(predict(tr,te));tes.append(te)
 elif mode=='fixed_predev':
  te=df[df.season.isin(DEV4)];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S['2013-14'][0]))];pred=[predict(tr,te)];tes=[te]
 elif mode=='fit_dev_only_insample':
  te=df[df.season.isin(DEV4)];tr=te;pred=[predict(tr,te)];tes=[te]
 elif mode=='fit_all_pre2017_insample_dev':
  te=df[df.season.isin(DEV4)];tr=df[(df.Date>=pd.Timestamp(start))&(df.Date<pd.Timestamp(S['2017-18'][0]))];pred=[predict(tr,te)];tes=[te]
 c=np.concatenate(pred); y=np.concatenate([z.y.to_numpy() for z in tes]);out={}
 for g in T_GATE:
  take=np.abs(c)>=g;r=np.sign(c[take])*y[take];out[g]=(int(take.sum()),int((r>0).sum()),int((r<0).sum()),int((r==0).sum()))
 return out
starts=['2007-10-30','2008-10-28','2009-10-27','2010-10-26','2011-12-25','2012-10-30']
rank=[]
for st in starts:
 for folds in [DEV4,DEV3]:
  selerr=0;table={}
  for a in ALPHAS:
   z=fold_deltas(st,folds,a)
   if z is None:selerr=1e9;break
   stats,vals=z;table[a]=(stats,vals);selerr+=sum(abs(x-y) for x,y in zip(stats,TSEL[a]))*1000
  oe,orows=oos_score(st);rank.append((selerr+oe,st,len(folds),selerr,oe,table,orows))
rank.sort(key=lambda x:x[0]);print('TRAIN/FOLD TOP')
for r in rank[:10]:
 print('\nSCORE',r[0],'START',r[1],'NFOLDS',r[2],'SELERR',r[3],'OOSERR',r[4]);print('ALPHA TABLE',r[5]);print('OOS',r[6])
print('\nGATE MODES')
for st in starts:
 for mode in ['oof4','oof3','fixed_predev','fit_dev_only_insample','fit_all_pre2017_insample_dev']:
  try:
   g=gate_counts(st,mode);e=sum(abs(g[x][0]-T_GATE[x]) for x in T_GATE)
   print('START',st,'MODE',mode,'COUNT_ERR',e,'GATES',g)
  except Exception as ex:print('ERR',st,mode,repr(ex))
