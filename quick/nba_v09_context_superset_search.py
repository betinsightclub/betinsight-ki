import itertools, sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/css.sqlite.zip'); R=Path('/tmp/cssdb'); DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)

S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TDEVSTAT=np.array([.012949336036388814,.02695917735504505,.025827748983386023])
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
TA={10:(.009858199953276525,.03022947944542187,.03099032558293935),30:(.010448690894154566,.0300874616301412,.030785955809568222),100:(.01181166035632586,.029377116254404978,.02939163151319235),300:(.012949336036388814,.02695917735504505,.025827748983386023),1000:(.011899062924864978,.021358065322965913,.01913939031452916)}
DOM=['margin2h_vs_pregame_half','ht_margin','ht_margin_surprise','spread_close','total2h_vs_pregame_half','total_close','total_move','ht_total_surprise']
CT=np.array([-.8094746967645475,-.3325877729098592,-.27095763027679604,.24972916246690846,-.1656421906820333,.11024812552992498,.06462265416697556,-.04308359545971495])

con=sqlite3.connect(DB);o=pd.read_sql_query('select * from BettingOdds_History',con);d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con);con.close();d=d.drop_duplicates('GAME_ID')
r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']:r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose']);r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)];r=r.dropna(subset=['2H_HomeSpread','2H_Over']);r=r[r['2H_Over'].between(50,200)]
df=r.merge(d,on='GAME_ID',how='left',validate='many_to_one');q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q:df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6):df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy();df.Date=pd.to_datetime(df.Date);df['season']='other'
for s,(a,b) in S.items():df.loc[df.Date.between(a,b),'season']=s
df['ht_margin']=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY);df['ht_total']=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
df['actual']=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6));df['market2h']=-df['2H_HomeSpread'];df['y']=df.actual-df.market2h
preg=-df.HomeSpread_AtClose
F=pd.DataFrame(index=df.index)
F['margin2h_vs_pregame_half']=df.market2h-preg/2
F['ht_margin']=df.ht_margin
F['ht_margin_surprise']=df.ht_margin-preg/2
F['spread_close']=df.HomeSpread_AtClose
F['total2h_vs_pregame_half']=df['2H_Over']-df.Over_AtClose/2
F['total_close']=df.Over_AtClose
F['total_move']=df.Over_AtClose-df.Over_AtOpen
F['ht_total_surprise']=df.ht_total-df.Over_AtClose/2
# Structured optional context variables. Most are direct/raw versions of already engineered components;
# Ridge can behave differently with such correlated columns even though predictive information is unchanged.
F['market2h_margin']=df.market2h
F['h2_total']=df['2H_Over']
F['spread_open']=df.HomeSpread_AtOpen
F['spread_move']=df.HomeSpread_AtClose-df.HomeSpread_AtOpen
F['total_open']=df.Over_AtOpen
F['ht_total']=df.ht_total
F['pregame_half_margin']=preg/2
F['pregame_half_total']=df.Over_AtClose/2

OPTIONAL=['market2h_margin','h2_total','spread_open','spread_move','total_open','ht_total','pregame_half_margin','pregame_half_total']

def pred(tr,te,cols,alpha=300):
    sc=StandardScaler();A=sc.fit_transform(F.loc[tr.index,cols]);B=sc.transform(F.loc[te.index,cols]);m=Ridge(alpha=alpha,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B),m

def stat(z,gate):
    k=np.abs(z['c'])>=gate;r=np.sign(z.loc[k,'c'].to_numpy())*z.loc[k,'y'].to_numpy();return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))

def evaluate(cols,full=False):
    dev=[];deltas=[]
    for s in DEV:
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c,_=pred(tr,te,cols,300);dev.append(pd.DataFrame({'c':c,'y':te.y.to_numpy()}));b=np.sqrt(np.mean(te.y.to_numpy()**2));m=np.sqrt(np.mean((te.y.to_numpy()-c)**2));deltas.append(b-m)
    dz=pd.concat(dev,ignore_index=True);ds=np.array([min(deltas),np.mean(deltas),np.median(deltas)])
    g={x:stat(dz,x) for x in TG}
    oos=[];orm=0;obet=0
    for s,t in TO.items():
        te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c,_=pred(tr,te,cols,300);rm=float(np.sqrt(np.mean((te.y.to_numpy()-c)**2)));z=pd.DataFrame({'c':c,'y':te.y.to_numpy()});b=stat(z,.75);oos.append((s,rm,b));orm+=abs(rm-t[0]);obet+=sum(abs(a-bb) for a,bb in zip(b,t[1:]))
    gerr=sum(sum(abs(a-b) for a,b in zip(g[x],TG[x])) for x in TG)
    dserr=float(np.abs(ds-TDEVSTAT).sum())
    score=dserr*2500+gerr*.08+orm*1500+obet*.08
    out={'score':score,'ds':ds,'g':g,'oos':oos,'dserr':dserr,'gerr':gerr,'orm':orm,'obet':obet}
    if full:
        ae=0;at={}
        for a,tgt in TA.items():
            vals=[]
            for s in DEV:
                te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];c,_=pred(tr,te,cols,a);b=np.sqrt(np.mean(te.y.to_numpy()**2));m=np.sqrt(np.mean((te.y.to_numpy()-c)**2));vals.append(b-m)
            st=np.array([min(vals),np.mean(vals),np.median(vals)]);e=float(np.abs(st-np.array(tgt)).sum());ae+=e;at[a]=(st,e)
        # Coefficients on development-only fit; compare only the named dominant columns if present.
        tr=df[df.season.isin(DEV)];sc=StandardScaler();A=sc.fit_transform(F.loc[tr.index,cols]);m=Ridge(alpha=300).fit(A,tr.y.to_numpy());coef=dict(zip(cols,m.coef_));cv=np.array([coef[x] for x in DOM]);cd=float(np.linalg.norm(cv-CT))
        out.update({'alphaerr':ae,'alphas':at,'coefdist':cd,'coefdom':cv})
    return out

results=[]
for bits in itertools.product([0,1], repeat=len(OPTIONAL)):
    extras=[x for x,b in zip(OPTIONAL,bits) if b];cols=DOM+extras
    z=evaluate(cols,False);results.append((z['score'],extras,z))
results.sort(key=lambda x:x[0])
print('N_CANDIDATES',len(results),'BASE8_RANK',next(i+1 for i,x in enumerate(results) if not x[1]))
print('\nTOP_STAGE1')
for i,(score,extras,z) in enumerate(results[:25],1):
    print('\nRANK',i,'SCORE',score,'EXTRAS',extras);print('DEVSTAT',z['ds'],'ERR',z['dserr']);print('GATE75',z['g'][.75],'TARGET',TG[.75],'GERR_ALL',z['gerr']);print('OOS',z['oos'],'RMERR',z['orm'],'BETERR',z['obet'])
print('\nFULL_TOP')
for i,(score,extras,z0) in enumerate(results[:20],1):
    cols=DOM+extras;z=evaluate(cols,True);final=z['score']+z['alphaerr']*3000+z['coefdist']*15
    print('\nRANK0',i,'FINAL',final,'STAGE1',z['score'],'EXTRAS',extras);print('ALPHAERR',z['alphaerr'],'ALPHAS',z['alphas']);print('COEFDIST',z['coefdist'],'COEFDOM',dict(zip(DOM,z['coefdom'])));print('DEVSTAT',z['ds']);print('GATES',z['g']);print('OOS',z['oos'])
