import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/scaler.sqlite.zip');R=Path('/tmp/scalerdb');DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
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

PRE2013=df[df.Date<pd.Timestamp(S['2013-14'][0])].index
DEVALL=df[df.season.isin(DEV)].index
PRE2017=df[df.Date<pd.Timestamp(S['2017-18'][0])].index
ALL=df.index

class FixedScaler:
    def __init__(self,idx,with_mean=True,ddof=0):
        a=X.loc[idx].to_numpy(float);self.mu=a.mean(0) if with_mean else np.zeros(a.shape[1]);self.sd=a.std(0,ddof=ddof);self.sd=np.where(self.sd==0,1,self.sd)
    def transform(self,a):return (np.asarray(a,float)-self.mu)/self.sd

def partial_transform(train,test,scaled_cols,reference='train'):
    ai=X.loc[train].to_numpy(float);bi=X.loc[test].to_numpy(float);A=ai.copy();B=bi.copy();inds=[NAMES.index(c) for c in scaled_cols]
    if reference=='train':ref=ai
    elif reference=='train_test':ref=np.vstack([ai,bi])
    else:ref=X.loc[reference].to_numpy(float)
    mu=ref[:,inds].mean(0);sd=ref[:,inds].std(0);sd=np.where(sd==0,1,sd)
    A[:,inds]=(A[:,inds]-mu)/sd;B[:,inds]=(B[:,inds]-mu)/sd
    return A,B

MODES=['train_std','train_std_ddof1','train_no_mean','fixed_pre2013','fixed_dev','fixed_pre2017','fixed_all','train_plus_test','derived_only','raw_market_only','all_except_total_move','all_except_raw_closes','all_except_ht_margin','l2norm_legacy']
DERIVED=['margin2h_vs_pregame_half','ht_margin_surprise','total2h_vs_pregame_half','total_move','ht_total_surprise']
RAW_MARKET=['spread_close','total_close','total_move']

def matrices(mode,tr_idx,te_idx):
    a=X.loc[tr_idx].to_numpy(float);b=X.loc[te_idx].to_numpy(float)
    if mode=='train_std':
        sc=StandardScaler().fit(a);return sc.transform(a),sc.transform(b)
    if mode=='train_std_ddof1':
        mu=a.mean(0);sd=a.std(0,ddof=1);sd=np.where(sd==0,1,sd);return (a-mu)/sd,(b-mu)/sd
    if mode=='train_no_mean':
        sc=StandardScaler(with_mean=False).fit(a);return sc.transform(a),sc.transform(b)
    if mode.startswith('fixed_'):
        mp={'fixed_pre2013':PRE2013,'fixed_dev':DEVALL,'fixed_pre2017':PRE2017,'fixed_all':ALL};sc=FixedScaler(mp[mode]);return sc.transform(a),sc.transform(b)
    if mode=='train_plus_test':
        sc=StandardScaler().fit(np.vstack([a,b]));return sc.transform(a),sc.transform(b)
    if mode=='derived_only':return partial_transform(tr_idx,te_idx,DERIVED)
    if mode=='raw_market_only':return partial_transform(tr_idx,te_idx,RAW_MARKET)
    if mode=='all_except_total_move':return partial_transform(tr_idx,te_idx,[c for c in NAMES if c!='total_move'])
    if mode=='all_except_raw_closes':return partial_transform(tr_idx,te_idx,[c for c in NAMES if c not in ['spread_close','total_close']])
    if mode=='all_except_ht_margin':return partial_transform(tr_idx,te_idx,[c for c in NAMES if c!='ht_margin'])
    if mode=='l2norm_legacy':
        # Approximate old sklearn normalize=True semantics: center then divide each feature by L2 norm.
        mu=a.mean(0);ac=a-mu;bc=b-mu;norm=np.sqrt((ac*ac).sum(0));norm=np.where(norm==0,1,norm);return ac/norm,bc/norm
    raise ValueError(mode)

def fit(mode,tr,te,a):
    A,B=matrices(mode,tr.index,te.index);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B)
def bs(c,y,g):
    k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))
def evaluate(mode,fullalpha=False):
    dev=[];ds=[]
    for s in DEV:
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c=fit(mode,tr,te,300);y=te.y.to_numpy();dev.append((c,y));ds.append(float(np.sqrt(np.mean(y*y))-np.sqrt(np.mean((y-c)**2))))
    c=np.concatenate([z[0] for z in dev]);y=np.concatenate([z[1] for z in dev]);st=(min(ds),float(np.mean(ds)),float(np.median(ds)));gates={g:bs(c,y,g) for g in TG};d300=sum(abs(a-b) for a,b in zip(st,TA[300]));gerr=sum(sum(abs(a-b) for a,b in zip(gates[g],TG[g])) for g in TG)
    out=[];rmerr=berr=0
    for s,t in TO.items():
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];cc=fit(mode,tr,te,300);yy=te.y.to_numpy();rm=float(np.sqrt(np.mean((yy-cc)**2)));bb=bs(cc,yy,.75);rmerr+=abs(rm-t[0]);berr+=sum(abs(a-b) for a,b in zip(bb,t[1:]));out.append((s,rm,bb))
    score=d300*5000+gerr*.12+rmerr*2500+berr*.12
    ae=None;at=None
    if fullalpha:
        ae=0;at={}
        for alpha,tgt in TA.items():
            dd=[]
            for s in DEV:
                te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];p=fit(mode,tr,te,alpha);yy=te.y.to_numpy();dd.append(float(np.sqrt(np.mean(yy*yy))-np.sqrt(np.mean((yy-p)**2))))
            ss=(min(dd),float(np.mean(dd)),float(np.median(dd)));er=sum(abs(a-b) for a,b in zip(ss,tgt));ae+=er;at[alpha]=(ss,er)
    return score,st,gates,gerr,out,rmerr,berr,ae,at

res=[]
for mode in MODES:
    try:res.append((evaluate(mode,False)[0],mode,evaluate(mode,False)))
    except Exception as e:print('MODE_ERROR',mode,repr(e))
res.sort()
print('RANKED SCALER MODES')
for rank,(score,mode,z) in enumerate(res,1):print('\nRANK',rank,'MODE',mode,'SCORE',score,'DEV',z[1],'G75',z[2][.75],'GERR',z[3],'RMERR',z[5],'BETERR',z[6],'GATES',z[2],'OOS',z[4])
print('\nFULL ALPHA ALL MODES')
for score,mode,z0 in res:
    z=evaluate(mode,True);print('\nMODE',mode,'STAGE_SCORE',score,'ALPHAERR',z[7]);print('ALPHAS',z[8]);print('GATES',z[2]);print('OOS',z[4])
