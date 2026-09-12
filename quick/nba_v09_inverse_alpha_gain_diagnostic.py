import sqlite3, urllib.request, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

URL='https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip'
Z=Path('/tmp/inv.sqlite.zip');R=Path('/tmp/invdb');DB=R/'basketball-final.sqlite'
if not DB.exists():
    R.mkdir(exist_ok=True); urllib.request.urlretrieve(URL,Z)
    with zipfile.ZipFile(Z) as z:z.extractall(R)
S={'2007-08':('2007-10-30','2008-04-16'),'2008-09':('2008-10-28','2009-04-15'),'2009-10':('2009-10-27','2010-04-14'),'2010-11':('2010-10-26','2011-04-13'),'2011-12':('2011-12-25','2012-04-26'),'2012-13':('2012-10-30','2013-04-17'),'2013-14':('2013-10-29','2014-04-16'),'2014-15':('2014-10-28','2015-04-15'),'2015-16':('2015-10-27','2016-04-13'),'2016-17':('2016-10-25','2017-04-12'),'2017-18':('2017-10-17','2018-04-11'),'2018-19':('2018-10-16','2019-04-10'),'2019-20':('2019-10-22','2020-08-14'),'2020-21':('2020-12-22','2021-05-16'),'2021-22':('2021-10-19','2021-12-20')}
DEV=['2013-14','2014-15','2015-16','2016-17']; OOS=['2017-18','2018-19','2019-20','2020-21','2021-22']
TARGET_BETS={'2017-18':332,'2018-19':295,'2019-20':246,'2020-21':195,'2021-22':89}
TARGET_WLP={'2017-18':(168,157,7),'2018-19':(155,131,9),'2019-20':(140,101,5),'2020-21':(99,91,5),'2021-22':(43,44,2)}
TARGET_RMSE={'2017-18':9.858216869241469,'2018-19':10.149329971984457,'2019-20':10.288966913270224,'2020-21':10.481849926111051,'2021-22':10.767341369515634}
TARGET_DEV75=(664,354,293,17)
TARGET_GATES={.25:(2841,1426,1345,70),.5:(1419,716,667,36),.75:(664,354,293,17),1:(302,158,136,8),1.25:(129,68,56,5),1.5:(50,29,19,2),2:(12,9,3,0)}

con=sqlite3.connect(DB)
o=pd.read_sql_query('select * from BettingOdds_History',con)
d=pd.read_sql_query('select GAME_ID,PTS_QTR1_HOME,PTS_QTR2_HOME,PTS_QTR3_HOME,PTS_QTR4_HOME,PTS_QTR1_AWAY,PTS_QTR2_AWAY,PTS_QTR3_AWAY,PTS_QTR4_AWAY,PTS_OT1_HOME,PTS_OT2_HOME,PTS_OT3_HOME,PTS_OT4_HOME,PTS_OT5_HOME,PTS_OT1_AWAY,PTS_OT2_AWAY,PTS_OT3_AWAY,PTS_OT4_AWAY,PTS_OT5_AWAY from Game_FullDetails',con)
con.close(); d=d.drop_duplicates('GAME_ID')
r=o[o.GAME_ID.isin(set(d.GAME_ID))].copy()
for c in ['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose','2H_HomeSpread','2H_Over']: r[c]=pd.to_numeric(r[c],errors='coerce')
r=r.dropna(subset=['HomeSpread_AtOpen','HomeSpread_AtClose','Over_AtOpen','Over_AtClose'])
r=r[r.HomeSpread_AtOpen.abs().le(30)&r.HomeSpread_AtClose.abs().le(30)&r.Over_AtOpen.between(100,300)&r.Over_AtClose.between(100,300)]
r=r.dropna(subset=['2H_HomeSpread','2H_Over']); r=r[r['2H_Over'].between(50,200)]
df=r.merge(d,on='GAME_ID',how='left',validate='many_to_one')
q=['PTS_QTR1_HOME','PTS_QTR2_HOME','PTS_QTR3_HOME','PTS_QTR4_HOME','PTS_QTR1_AWAY','PTS_QTR2_AWAY','PTS_QTR3_AWAY','PTS_QTR4_AWAY']
for c in q: df[c]=pd.to_numeric(df[c],errors='coerce')
for side in ['HOME','AWAY']:
    for i in range(1,6): df[f'PTS_OT{i}_{side}']=pd.to_numeric(df[f'PTS_OT{i}_{side}'],errors='coerce').fillna(0)
df=df.dropna(subset=q).copy(); df.Date=pd.to_datetime(df.Date); df['season']='other'
for s,(a,b) in S.items(): df.loc[df.Date.between(pd.Timestamp(a),pd.Timestamp(b)),'season']=s
htm=(df.PTS_QTR1_HOME+df.PTS_QTR2_HOME)-(df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY)
htt=df.PTS_QTR1_HOME+df.PTS_QTR2_HOME+df.PTS_QTR1_AWAY+df.PTS_QTR2_AWAY
actual=(df.PTS_QTR3_HOME+df.PTS_QTR4_HOME)-(df.PTS_QTR3_AWAY+df.PTS_QTR4_AWAY)+sum(df[f'PTS_OT{i}_HOME']-df[f'PTS_OT{i}_AWAY'] for i in range(1,6))
market=-df['2H_HomeSpread']; preg=-df.HomeSpread_AtClose; df['y']=actual-market
X=pd.DataFrame({'margin2h_vs_pregame_half':market-preg/2,'ht_margin':htm,'ht_margin_surprise':htm-preg/2,'spread_close':df.HomeSpread_AtClose,'total2h_vs_pregame_half':df['2H_Over']-df.Over_AtClose/2,'total_close':df.Over_AtClose,'total_move':df.Over_AtClose-df.Over_AtOpen,'ht_total_surprise':htt-df.Over_AtClose/2},index=df.index)

def pred_for(s,alpha=300):
    te=df[df.season==s]; tr=df[df.Date<pd.Timestamp(S[s][0])]
    sc=StandardScaler(); A=sc.fit_transform(X.loc[tr.index]); B=sc.transform(X.loc[te.index]); m=Ridge(alpha=alpha,fit_intercept=True).fit(A,tr.y.to_numpy())
    return te.index.to_numpy(),m.predict(B),te.y.to_numpy(),len(tr)
def bs(c,y,g=.75):
    k=np.abs(c)>=g; r=np.sign(c[k])*y[k]
    return (int(k.sum()),int((r>1e-12).sum()),int((r<-1e-12).sum()),int((np.abs(r)<=1e-12).sum()))
def rmse(c,y): return float(np.sqrt(np.mean((y-c)**2)))
def wlp_err(b,t): return sum(abs(a-bb) for a,bb in zip(b,t))

print('=== PER-SEASON INVERSE DIAGNOSTIC ===')
for s in OOS:
    idx,c300,y,ntr=pred_for(s,300)
    print('\nSEASON',s,'NTRAIN',ntr,'BASE_ALPHA300_RMSE',rmse(c300,y),'BASE_BETS',bs(c300,y),'TARGET_RMSE',TARGET_RMSE[s],'TARGET_BETS',(TARGET_BETS[s],)+TARGET_WLP[s])
    # alpha grid: optimize count, full WLP, RMSE, and combined separately
    ar=[]
    for a in range(50,601):
        _,c,y2,_=pred_for(s,a); b=bs(c,y2); r=rmse(c,y2)
        count_err=abs(b[0]-TARGET_BETS[s]); werr=wlp_err(b[1:],TARGET_WLP[s]); re=abs(r-TARGET_RMSE[s])
        ar.append((count_err,werr,re,a,r,b,float(np.std(c)),float(np.mean(np.abs(c)))))
    for label,key in [('COUNT',lambda z:(z[0],z[1],z[2])),('WLP',lambda z:(z[1],z[0],z[2])),('RMSE',lambda z:(z[2],z[0]+z[1])),('COMBINED',lambda z:(z[0]*2+z[1]+z[2]*1000,z[2]))]:
        z=min(ar,key=key); print('BEST_ALPHA_'+label,'alpha',z[3],'rmse',z[4],'bets',z[5],'count_err',z[0],'wlp_err',z[1],'rmse_err',z[2],'pred_sd',z[6],'mean_abs',z[7])
    # gain grid on fixed alpha300 predictions
    gr=[]
    for g in np.arange(.70,1.301,.001):
        cc=c300*g; b=bs(cc,y); r=rmse(cc,y); count_err=abs(b[0]-TARGET_BETS[s]); werr=wlp_err(b[1:],TARGET_WLP[s]); re=abs(r-TARGET_RMSE[s]); gr.append((count_err,werr,re,float(g),r,b))
    for label,key in [('COUNT',lambda z:(z[0],z[1],z[2])),('WLP',lambda z:(z[1],z[0],z[2])),('RMSE',lambda z:(z[2],z[0]+z[1])),('COMBINED',lambda z:(z[0]*2+z[1]+z[2]*1000,z[2]))]:
        z=min(gr,key=key); print('BEST_GAIN_'+label,'gain',z[3],'rmse',z[4],'bets',z[5],'count_err',z[0],'wlp_err',z[1],'rmse_err',z[2])

print('\n=== DEVELOPMENT POOLED INVERSE ===')
# cache alpha300 dev predictions by season
cache=[]
for s in DEV:
    idx,c,y,n=pred_for(s,300); cache.append((s,c,y,n))
c300=np.concatenate([z[1] for z in cache]); y=np.concatenate([z[2] for z in cache])
print('BASE300_GATES',{g:bs(c300,y,g) for g in TARGET_GATES})
# gain minimizing full gate-table L1
best=[]
for gain in np.arange(.80,1.251,.001):
    cc=c300*gain; gates={g:bs(cc,y,g) for g in TARGET_GATES}; err=sum(sum(abs(a-b) for a,b in zip(gates[g],TARGET_GATES[g])) for g in TARGET_GATES); best.append((err,float(gain),gates))
for z in sorted(best)[:15]: print('DEV_GAIN','err',z[0],'gain',z[1],'gates',z[2])
# single alpha minimizing full gate table, recompute seasonally
rows=[]
for a in range(50,601):
    zz=[]
    for s in DEV:
        _,c,y2,_=pred_for(s,a); zz.append((c,y2))
    c=np.concatenate([v[0] for v in zz]); yy=np.concatenate([v[1] for v in zz]); gates={g:bs(c,yy,g) for g in TARGET_GATES}; err=sum(sum(abs(u-v) for u,v in zip(gates[g],TARGET_GATES[g])) for g in TARGET_GATES); rows.append((err,a,gates))
for z in sorted(rows)[:15]: print('DEV_ALPHA','err',z[0],'alpha',z[1],'gates',z[2])
