import itertools, sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/gain.sqlite.zip');R=Path('/tmp/gaindb');DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17'];OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TG={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}
TO={'2017-18':(9.858216869241469,332,168,157,7),'2018-19':(10.149329971984457,295,155,131,9),'2019-20':(10.288966913270224,246,140,101,5),'2020-21':(10.481849926111051,195,99,91,5),'2021-22':(10.767341369515634,89,43,44,2)}
CT=np.array([-.8094746967645475,-.3325877729098592,-.27095763027679604,.24972916246690846,-.1656421906820333,.11024812552992498,.06462265416697556,-.04308359545971495])
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

def makeX(t2='close_half',hts='close_half'):
    if t2=='close_half': a=df['2H_Over']-df.Over_AtClose/2
    elif t2=='open_half': a=df['2H_Over']-df.Over_AtOpen/2
    elif t2=='avg_half': a=df['2H_Over']-(df.Over_AtOpen+df.Over_AtClose)/4
    elif t2=='close_full': a=df['2H_Over']-df.Over_AtClose
    if hts=='close_half': b=htt-df.Over_AtClose/2
    elif hts=='open_half': b=htt-df.Over_AtOpen/2
    elif hts=='avg_half': b=htt-(df.Over_AtOpen+df.Over_AtClose)/4
    elif hts=='close_full': b=htt-df.Over_AtClose
    return pd.DataFrame({'margin2h_vs_pregame_half':market-preg/2,'ht_margin':htm,'ht_margin_surprise':htm-preg/2,'spread_close':df.HomeSpread_AtClose,'total2h_vs_pregame_half':a,'total_close':df.Over_AtClose,'total_move':df.Over_AtClose-df.Over_AtOpen,'ht_total_surprise':b},index=df.index)
X=makeX()
def fit(tr,te,a=300):
    sc=StandardScaler();A=sc.fit_transform(X.loc[tr.index]);B=sc.transform(X.loc[te.index]);m=Ridge(alpha=a,fit_intercept=True).fit(A,tr.y.to_numpy());return m.predict(B)
def bst(c,y,g):
    k=np.abs(c)>=g;r=np.sign(c[k])*y[k];return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))
# Cache seasonal predictions once.
dev=[];oos={}
for s in DEV:
    te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];dev.append((s,fit(tr,te),te.y.to_numpy()))
for s in OOS:
    te=df[df.season==s];tr=df[df.Date<pd.Timestamp(S[s][0])];oos[s]=(fit(tr,te),te.y.to_numpy())
print('=== GAIN GRID ===')
rows=[]
for gain in np.arange(.90,1.251,.005):
    c=np.concatenate([z[1]*gain for z in dev]);y=np.concatenate([z[2] for z in dev]);gates={g:bst(c,y,g) for g in TG};gerr=sum(sum(abs(a-b) for a,b in zip(gates[g],TG[g])) for g in TG)
    rmerr=0;berr=0;out=[]
    for s,t in TO.items():
        cc=oos[s][0]*gain;yy=oos[s][1];rm=float(np.sqrt(np.mean((yy-cc)**2)));b=bst(cc,yy,.75);rmerr+=abs(rm-t[0]);berr+=sum(abs(a-bb) for a,bb in zip(b,t[1:]));out.append((s,rm,b))
    score=gerr*.12+berr*.12+rmerr*2500
    rows.append((score,gain,gates,gerr,out,rmerr,berr))
for i,r in enumerate(sorted(rows)[:20],1):
    print(i,'SCORE',r[0],'GAIN',r[1],'G75',r[2][.75],'GERR',r[3],'RMERR',r[5],'BETERR',r[6],'OOS',r[4])
print('\nCLOSEST G75 COUNT')
for r in sorted(rows,key=lambda z:(abs(z[2][.75][0]-664),sum(abs(a-b) for a,b in zip(z[2][.75],TG[.75])),z[0]))[:12]:print('GAIN',r[1],'G75',r[2][.75],'GATES',r[2],'OOS',r[4],'RMERR',r[5],'BETERR',r[6])

print('\n=== ROBUST COEFFICIENT SOURCE GRID ===')
tr=df[df.Date<pd.Timestamp(S['2017-18'][0])]
coefrows=[]
for t2,hts in itertools.product(['close_half','open_half','avg_half','close_full'],repeat=2):
    XX=makeX(t2,hts)
    for alpha in range(850,1151,10):
        sc=StandardScaler();A=sc.fit_transform(XX.loc[tr.index]);m=Ridge(alpha=alpha,fit_intercept=True).fit(A,tr.y.to_numpy());dist=float(np.linalg.norm(m.coef_-CT));coefrows.append((dist,t2,hts,alpha,m.coef_))
for i,(dist,t2,hts,a,c) in enumerate(sorted(coefrows)[:25],1):print(i,'DIST',dist,'T2',t2,'HTS',hts,'ALPHA',a,'COEFS',dict(zip(NAMES,c)))
