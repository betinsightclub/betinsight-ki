import itertools, sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
ZIP=Path('/tmp/basketball-final.sqlite.zip'); ROOT=Path('/tmp/nba_preprocess_fp'); DB=ROOT/'basketball-final.sqlite'
if not DB.exists():
    ROOT.mkdir(parents=True,exist_ok=True); urllib.request.urlretrieve(URL,ZIP)
    with zipfile.ZipFile(ZIP) as z:z.extractall(ROOT)

SEASONS={
'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),
'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),
'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),
'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),
'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
T_RMSE={'2017-18':9.858216869241469,'2018-19':10.149329971984457,'2019-20':10.288966913270224,'2020-21':10.481849926111051,'2021-22':10.767341369515634}
T_BETS={'2017-18':(332,168,157,7),'2018-19':(295,155,131,9),'2019-20':(246,140,101,5),'2020-21':(195,99,91,5),'2021-22':(89,43,44,2)}
T_DEV=(664,354,293,17); T_DEVSTAT=(0.012949336036388814,0.02695917735504505,0.025827748983386023)
COEF_T=np.array([-0.8094746967645475,-0.3325877729098592,-0.27095763027679604,0.24972916246690846,-0.1656421906820333,0.11024812552992498,0.06462265416697556,-0.04308359545971495])
F=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']

con=sqlite3.connect(DB); odds=pd.read_sql_query('select * from BettingOdds_History',con); det=pd.read_sql_query('''select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails''',con); con.close()
det=det.drop_duplicates('GAME_ID'); reg=odds[odds.GAME_ID.isin(set(det.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:reg[c]=pd.to_numeric(reg[c],errors='coerce')
reg=reg.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']); reg=reg[reg.HomeSpread_AtOpen.abs().le(30)&reg.HomeSpread_AtClose.abs().le(30)&reg.Over_AtOpen.between(100,300)&reg.Over_AtClose.between(100,300)]; reg=reg.dropna(subset=['2H_HomeSpread','2H_Over']); reg=reg[reg['2H_Over'].between(50,200)]
df=reg.merge(det,on='GAME_ID',how='left',validate='many_to_one')
q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
 for i in range(1,6):
  c=f'PTS_OT{i}_{side}';df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
df=df.dropna(subset=q);df['Date']=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in SEASONS.items():df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s
df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
df['reg2h_margin']=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)
otm=sum([df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6)])
df['actual2h']=df.reg2h_margin+otm;df['market2h']=-df['2H_HomeSpread'];df['edge_actual']=df.actual2h-df.market2h;df['edge_reg']=df.reg2h_margin-df.market2h

# Several narrowly plausible formulas for the named context features.
def feat(preg_source='close',ht_factor=.5,total_source='close',move='signed',m2_source='close'):
 sp=df.HomeSpread_AtClose if preg_source=='close' else df.HomeSpread_AtOpen
 pre_margin=-sp
 spm=df.HomeSpread_AtClose if m2_source=='close' else df.HomeSpread_AtOpen
 m2pre=-spm/2
 tot=df.Over_AtClose if total_source=='close' else df.Over_AtOpen
 mv=df.Over_AtClose-df.Over_AtOpen
 if move=='reverse':mv=-mv
 if move=='abs':mv=mv.abs()
 return pd.DataFrame({
 'margin2h_vs_pregame_half':df.market2h-m2pre,
 'ht_margin':df.ht_margin,
 'ht_margin_surprise':df.ht_margin-(pre_margin*ht_factor),
 'spread_close':df.HomeSpread_AtClose,
 'total2h_vs_pregame_half':df['2H_Over']-tot/2,
 'total_close':df.Over_AtClose,
 'total_move':mv,
 'ht_total_surprise':df.ht_total-tot/2},index=df.index)

def prep_fit(Xtr,Xte,y,mode,intercept,globalX=None):
 if mode=='std_train':
  sc=StandardScaler();A=sc.fit_transform(Xtr);B=sc.transform(Xte)
 elif mode=='std_global':
  sc=StandardScaler().fit(globalX);A=sc.transform(Xtr);B=sc.transform(Xte)
 elif mode=='raw':
  sc=None;A=Xtr.to_numpy();B=Xte.to_numpy()
 elif mode=='center':
  mu=Xtr.mean(axis=0).to_numpy();sc=None;A=Xtr.to_numpy()-mu;B=Xte.to_numpy()-mu
 else:raise ValueError(mode)
 m=Ridge(alpha=300,fit_intercept=intercept);m.fit(A,y);return m.predict(B),m,sc

def bet(te,c):
 take=np.abs(c)>=.75;r=np.sign(c[take])*te.edge_actual.to_numpy()[take]
 return (int(take.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def standardized_coef(model,sc,Xtrain,ytrain,mode):
 # Return effect per one train-set feature SD in response-point units.
 if mode.startswith('std'):return model.coef_.copy()
 sd=Xtrain.std(axis=0,ddof=0).to_numpy();return model.coef_*sd

res=[]
for preg_source,ht_factor,total_source,move,m2_source,prep,intercept,target in itertools.product(['close','open'],[.5,1.0],['close','open'],['signed','reverse','abs'],['close','open'],['std_train','std_global','raw','center'],[True,False],['incl_ot','reg_only']):
 X=feat(preg_source,ht_factor,total_source,move,m2_source); devd=[];devb=np.zeros(4,dtype=int);oos=[];rmerr=0;berr=0
 for s in DEV:
  te=df[df.season==s];tr=df[df.Date<pd.Timestamp(SEASONS[s][0])];yt=tr.edge_actual if target=='incl_ot' else tr.edge_reg
  pr,m,sc=prep_fit(X.loc[tr.index,F],X.loc[te.index,F],yt.to_numpy(),prep,intercept,X[F]); pred=te.market2h.to_numpy()+pr
  br=np.sqrt(np.mean(te.edge_actual.to_numpy()**2));mr=np.sqrt(np.mean((te.actual2h.to_numpy()-pred)**2));devd.append(br-mr);devb+=np.array(bet(te,pr))
 for s in OOS:
  te=df[df.season==s];tr=df[df.Date<pd.Timestamp(SEASONS[s][0])];yt=tr.edge_actual if target=='incl_ot' else tr.edge_reg
  pr,m,sc=prep_fit(X.loc[tr.index,F],X.loc[te.index,F],yt.to_numpy(),prep,intercept,X[F]);mr=np.sqrt(np.mean((te.actual2h.to_numpy()-(te.market2h.to_numpy()+pr))**2));b=bet(te,pr);oos.append((s,mr,b));rmerr+=abs(mr-T_RMSE[s]);berr+=sum(abs(a-z) for a,z in zip(b,T_BETS[s]))
 ds=(min(devd),float(np.mean(devd)),float(np.median(devd)));dserr=sum(abs(a-z) for a,z in zip(ds,T_DEVSTAT));dberr=sum(abs(int(a)-z) for a,z in zip(devb,T_DEV))
 # coefficient check on development-only fit
 tr=df[df.season.isin(DEV)];yt=tr.edge_actual if target=='incl_ot' else tr.edge_reg
 _,m,sc=prep_fit(X.loc[tr.index,F],X.loc[tr.index[:1],F],yt.to_numpy(),prep,intercept,X[F]);coef=standardized_coef(m,sc,X.loc[tr.index,F],yt,prep);cd=float(np.linalg.norm(coef-COEF_T))
 score=rmerr*1000+(berr+dberr)*.05+dserr*1000+cd*10
 res.append((score,(preg_source,ht_factor,total_source,move,m2_source,prep,intercept,target),ds,tuple(devb),oos,rmerr,berr,dberr,cd,coef))
res.sort(key=lambda z:z[0])
print('CLEAN',len(df),'TOP')
for i,r in enumerate(res[:20],1):
 print('\nRANK',i,'SCORE',r[0],'SPEC',r[1]);print('DEVSTAT',r[2],'TARGET',T_DEVSTAT);print('DEVBETS',r[3],'TARGET',T_DEV);print('OOS',r[4]);print('ERR rmse/bet/devbet/coef',r[5],r[6],r[7],r[8]);print('COEF',dict(zip(F,r[9])))
