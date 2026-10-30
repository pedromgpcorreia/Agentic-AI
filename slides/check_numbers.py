# Each number shown in the slides is recomputed from raw outputs and looked up in the slide text.
import pandas as pd,numpy as np,re
from scipy import stats
import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, "/") + "/"
R=ROOT;D=ROOT+"slides/src/slides/"
T=lambda s:open(D+s+".html",encoding="utf8").read()
bad=0;n=0
def chk(slide,txt,val=None):
    global bad,n;n+=1;ok=txt in T(slide);bad+=not ok
    print(("ok  " if ok else "FAIL"),slide,repr(txt),"" if val is None else f"(raw {val})")
def f(v,d=1,s=False):
    t=f"{abs(v):.{d}f}";return ("+" if v>=0 else "−")+t if s else t
ci=lambda x:(np.mean(x),)+tuple(np.mean(x)+k*stats.t.ppf(.975,len(x)-1)*np.std(x,ddof=1)/np.sqrt(len(x)) for k in(-1,1))
b=pd.read_csv(R+"data/baseline.csv.gz");x=b[b.tick==1000];s=x.orange/100
m,l,h=ci(x.clustering);chk("baseline",f"{m:.3f}",m);chk("baseline",f"{l:.3f}–{h:.3f}");chk("baseline",f"{s.mean():.3f}");chk("baseline",f"{s.std():.3f}")
chk("baseline",f"{s.quantile(.05):.2f} and {s.quantile(.95):.2f}");chk("baseline",f"{b[b.tick==2000].clustering.mean():.3f}");chk("baseline","1000 runs",x.shape[0])
e=pd.read_csv(R+"data/norm_influence.csv.gz");chk("baselinesens",f"{e[e.norm_influence==0].clustering.mean():.3f}")
e=pd.read_csv(R+"data/quality_blue.csv.gz");e["s"]=e.orange/(e.orange+e.blue);chk("baselinesens",f"{e[e.quality_blue==.45].s.mean():.3f}");chk("baselinesens",f"{e[e.quality_blue==.55].s.mean():.3f}")
e=pd.read_csv(R+"data/exploration.csv.gz");chk("baselinesens",f"{e[e.exploration==.2].clustering.mean():.3f}")
S=pd.read_csv(R+"results/pricing/series.csv.gz");r=pd.read_csv(R+"results/pricing/runs.csv");F=S[S.scenario=="fixed_1.00"].set_index("month");N=S[S.scenario=="no_entry"].set_index("month")
v=[F.share_DIGI[k]*100 for k in(19,25,28)]
for a in v:chk("calibration",f"{a:.1f}%",round(a,2))
chk("calibration",f"{np.sqrt(np.mean((np.array(v)-[2.8,3,3.2])**2)):.2f} pp")
for o,a in zip(("MEO","NOS","Vodafone"),("40.3","35.1","21.4")):chk("calibration",f"{F[f'share_{o}'][28]*100:.1f}")
M="bandit_e0.10_a0.2";ref=r[r.scenario=="fixed_1.00"].set_index("seed")
d=lambda sc,c:(lambda g:(g[c]-ref[c])/ref[c]*100)(r[r.scenario==sc].set_index("seed").loc[ref.index])
for sc,t in[("no_entry",None),(M,None),("bandit_p6",None),("bandit_p12",None),("fixed_0.95",None),("fixed_0.90",None),("fixed_0.85",None),("fixed_0.80",None)]:
    a=d(sc,"profit_incumbents").mean();chk("profit",f"{f(a).rjust(0)}" ,round(a,2))
a,l,h=ci(d(M,"profit_incumbents"));chk("profit",f"minus {abs(l):.1f} to minus {abs(h):.1f}")
for o in("MEO","NOS","Vodafone"):
    chk("dilemma",f(d(f"solo_{o}_0.90",f"profit_{o}").mean(),s=True));chk("dilemma",f(d("fixed_0.90",f"profit_{o}").mean(),s=True))
J=[d(f"solo_{o}_0.90","profit_incumbents").mean() for o in("MEO","NOS","Vodafone")];chk("dilemma",f"{abs(max(J)):.1f} to {abs(min(J)):.1f}")
for o,w in(("MEO","minus"),("NOS","minus"),("Vodafone","plus")):chk("dilemma",f"{w} {abs(d(f'solo_{o}_0.80',f'profit_{o}').mean()):.1f}")
B={"MEO":42.49,"NOS":42.49,"Vodafone":40.5};mu=lambda sc:np.mean([S[S.scenario==sc].set_index("month")[f"price_{o}"][13:].mean()/B[o] for o in B])
chk("prices",f"{mu(M):.2f}");chk("profit",f"{mu('bandit_p6'):.2f} at 6 months");chk("profit",f"{mu('bandit_p12'):.2f} at 12 months")
C=[k for k in r.scenario.unique() if k.startswith("bandit_e")];P=[d(k,"profit_incumbents").mean() for k in C];ms=[mu(k) for k in C]
chk("prices",f"−{abs(max(P)):.1f}% to −{abs(min(P)):.1f}%");chk("prices",f"{min(ms):.2f}–{max(ms):.2f}")
l_=pd.read_csv(R+"results/pricing/bandit_log.csv.gz");ll=l_[(l_.scenario==M)&(l_.month>72)];print("  list share",ll.groupby("operator").new_arm.apply(lambda z:round((z==1).mean()*100)).to_dict());chk("prices","85 percent");chk("prices","88 for NOS");chk("prices","88 for Vodafone")
chk("prices",f"{(ll[~ll.explored].new_arm==1).mean()*100:.0f} percent");chk("prices",f"{ll.explored.mean()*100:.0f} percent")
for sc in("fixed_1.00",M,"fixed_0.90"):chk("digi",f"{r[r.scenario==sc].share_DIGI_end.mean()*100:.1f}%")
chk("limits",f"{N.share_MEO[12]*100:.1f}% to {N.share_MEO[72]*100:.1f}%");chk("limits",f"{N.share_DIGI[12]*100:.1f}% to {N.share_DIGI[72]*100:.1f}%")
q=pd.read_csv(R+"results/sensitivity/runs.csv");Z={o:[] for o in B};JJ=[];MM=[]
for v_,g in q.groupby("variant"):
    rf=g[g.scenario=="fixed_1.00"].set_index("seed")
    for o in B:
        y=g[g.scenario==f"solo_{o}_0.90"].set_index("seed").loc[rf.index];Z[o].append(((y[f"profit_{o}"]-rf[f"profit_{o}"])/rf[f"profit_{o}"]*100).mean())
    y=g[g.scenario=="bandit"].set_index("seed").loc[rf.index];JJ.append(((y.profit_incumbents-rf.profit_incumbents)/rf.profit_incumbents*100).mean());MM.append(np.mean([(y[f"price_{o}_mean"]/B[o]).mean() for o in B]))
print("  variants",q.variant.nunique(),"incl. base; MEO min",round(min(Z["MEO"]),2))
chk("sensitivity",f"+{min(Z['NOS']):.1f}% to +{max(Z['NOS']):.1f}%");chk("sensitivity",f"+{min(Z['Vodafone']):.1f}% to +{max(Z['Vodafone']):.1f}%");chk("sensitivity",f"−{abs(min(Z['MEO'])):.1f}%");chk("sensitivity",f"{min(MM):.2f}–{max(MM):.2f}");chk("sensitivity",f"−{abs(max(JJ)):.1f}% to −{abs(min(JJ)):.1f}%")
m28=q[q.scenario=="fixed_1.00"].groupby("variant").share_DIGI_m28.mean()*100;chk("sensitivity",f"{m28['kappa_0.10']:.2f} percent");chk("sensitivity",f"{m28['kappa_0.30']:.2f} percent")
print(f"\n{n} checks, {bad} failed")
