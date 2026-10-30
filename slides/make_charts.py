# All slide charts, computed directly from the raw outputs in the repository.
import pandas as pd,numpy as np,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
from scipy import stats
import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, "/") + "/"
R=ROOT;A=ROOT+"slides/assets/"
BG,INK,INK2,GRID="#F8F7F2","#1C2230","#55595F","#E2E0D8"
C={"MEO":"#2a78d6","NOS":"#eb6834","Vodafone":"#1a9e77","DIGI":"#7a3fbf"}
plt.rcParams.update({"font.family":"Arial","font.size":17.3,"axes.facecolor":BG,"figure.facecolor":BG,"savefig.facecolor":BG,
 "axes.edgecolor":INK2,"text.color":INK,"axes.labelcolor":INK2,"xtick.color":INK2,"ytick.color":INK2,"axes.grid":True,"grid.color":GRID,"grid.linewidth":1,
 "axes.spines.top":False,"axes.spines.right":False,"lines.linewidth":3,"legend.frameon":False,"axes.axisbelow":True})
def fig(w,h,*a,**k): return plt.subplots(*a,figsize=(w/100,h/100),**k)
def save(f,n): f.tight_layout(pad=.6);f.savefig(A+n+".png",dpi=200);plt.close(f)
def ci(x):
    x=np.asarray(x,float);h=stats.t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x));return x.mean(),x.mean()-h,x.mean()+h
OPS=["MEO","NOS","Vodafone"]
# task 2: baseline
b=pd.read_csv(R+"data/baseline.csv.gz");x=b[b.tick==1000]
g=b.groupby("tick").clustering.mean()
f,(a1,a2)=fig(1660,600,1,2)
a1.plot(g.index[:1001],g.values[:1001],color=C["MEO"]);a1.set(xlabel="Tick",ylabel="Mean clustering",ylim=(.4,1),title="");a1.annotate(f"{g[1000]:.3f} at tick 1000",(1000,g[1000]),(560,.82),color=INK)
a2.hist(x.orange,bins=np.arange(0,102,5),color=C["NOS"],edgecolor=BG,linewidth=2);a2.set(xlabel="Orange share at tick 1000 (%)",ylabel="Runs (of 1000)");a2.grid(axis="x",visible=False)
save(f,"baseline")
# task 2: sensitivity
f,ax=fig(1660,560,1,3,sharey=True)
for a,n,l in zip(ax,["norm_influence","quality_blue","exploration"],["Norm influence","Quality of blue (orange = 0.5)","Exploration"]):
    e=pd.read_csv(R+f"data/{n}.csv.gz");m=e.groupby(n).clustering.mean();a.plot(m.index,m.values,"o-",ms=9,color=C["MEO"],label="Clustering")
    s=(e.orange/(e.orange+e.blue)).groupby(e[n]).mean();a.plot(s.index,s.values,"s-",ms=8,color=C["NOS"],label="Orange share");a.set(xlabel=l,ylim=(0,1.03))
ax[0].set_ylabel("Mean at tick 1000");ax[0].legend(loc="lower right")
save(f,"baseline_sens")
s=pd.read_csv(R+"results/pricing/series.csv.gz");r=pd.read_csv(R+"results/pricing/runs.csv");M="bandit_e0.10_a0.2"
q=lambda n:s[s.scenario==n].set_index("month")
# task 3: calibration
f,a=fig(1000,640);F=q("fixed_1.00");a.plot(F.index[:37],F.share_DIGI[:37]*100,color=C["DIGI"],label="Model, mean of 30 runs")
a.scatter([10,19,25,28],[2.6,2.8,3.0,3.2],color=INK,s=110,zorder=5,label="ANACOM")
a.axvline(12,color=INK2,lw=1.5,ls="--");a.text(12.4,4.0,"DIGI enters\n(month 12)",color=INK2)
a.set(xlabel="Month (0 = Nov 2023)",ylabel="NOWO/DIGI share (%)",ylim=(0,4.5),xlim=(0,36));a.legend(loc="lower right");save(f,"calibration")
# task 5: profit bars
order=[("no_entry","No DIGI entry"),("fixed_1.00","All at list price"),(M,"Learned, every 3 months"),("bandit_p6","Learned, every 6 months"),("bandit_p12","Learned, every 12 months"),("fixed_0.95","All at ×0.95"),("fixed_0.90","All at ×0.90"),("fixed_0.85","All at ×0.85"),("fixed_0.80","All at ×0.80")]
ref=r[r.scenario=="fixed_1.00"].set_index("seed");f,a=fig(1660,640)
for i,(sc,l) in enumerate(order):
    g_=r[r.scenario==sc].set_index("seed").loc[ref.index];m,lo,hi=ci((g_.profit_incumbents-ref.profit_incumbents)/ref.profit_incumbents*100)
    col=C["DIGI"] if sc.startswith("bandit") else "#8C8F94"
    a.barh(i,m,color=col,height=.62);
    if sc!="fixed_1.00":a.errorbar(m,i,xerr=[[m-lo],[hi-m]],color=INK,capsize=4,lw=1.5)
    dg=f"DIGI {g_.share_DIGI_end.mean()*100:.1f}%" if sc!="no_entry" else "no DIGI"
    txt=("reference" if sc=="fixed_1.00" else f"{m:+.1f}%".replace("-","−"))+"  ·  "+dg
    a.text((hi if sc=="no_entry" else 0)+1.2,i,txt,va="center",color=INK)
a.set_yticks(range(len(order)),[l for _,l in order]);a.invert_yaxis();a.axvline(0,color=INK,lw=1.5);a.set(xlabel="Joint incumbent profit over 10 years, % vs all at list price",xlim=(-45,38));a.grid(axis="y",visible=False);save(f,"profit")
# task 5: learned prices
f,(a1,a2)=fig(1660,600,1,2,gridspec_kw={"width_ratios":[1.5,1]});B={"MEO":42.49,"NOS":42.49,"Vodafone":40.5};Q=q(M)
for o,v in zip(OPS,[1,1,1]):a1.plot(Q.index,Q[f"price_{o}"]/B[o],color=C[o],label=o,lw=2.5)
a1.axvline(12,color=INK2,lw=1.5,ls="--");a1.set(xlabel="Month",ylabel="Mean price ÷ list price",ylim=(.84,1.01));a1.legend(loc="lower right",ncol=3)
l=pd.read_csv(R+"results/pricing/bandit_log.csv.gz");ll=l[(l.scenario==M)&(l.month>72)]
fr=ll.groupby("operator").new_arm.value_counts(normalize=True).unstack().reindex(OPS)*100
a2.barh(OPS,fr[1.0],color="#1C2230",height=.55,label="List price");a2.barh(OPS,100-fr[1.0],left=fr[1.0],color="#C9C7BF",height=.55,label="Any cut")
for i,o in enumerate(OPS):a2.text(fr[1.0][o]/2,i,f"{fr[1.0][o]:.0f}%",color="#F8F7F2",ha="center",va="center",fontweight="bold")
a2.invert_yaxis();a2.set(xlabel="Share of decisions, years 6–10 (%)",xlim=(0,100));a2.grid(visible=False);a2.legend(loc="upper center",bbox_to_anchor=(.5,1.17),ncol=2);save(f,"learned")
# task 5: DIGI paths
f,a=fig(1660,600)
for sc,l,c,ls in[("fixed_1.00","All at list price",INK2,"-"),(M,"Learned prices",C["DIGI"],"-"),("fixed_0.90","All at ×0.90","#8C8F94","--"),("no_entry","No entry (NOWO)","#8C8F94",":")]:
    z=q(sc);a.plot(z.index,z.share_DIGI*100,color=c,ls=ls);a.text(133,z.share_DIGI.iloc[-1]*100,f"{l}",color=INK,va="center")
a.axvline(12,color=INK2,lw=1.5,ls="--");a.set(xlabel="Month",ylabel="NOWO/DIGI share (%)",xlim=(0,175),ylim=(0,26));a.set_xticks(range(0,133,24));save(f,"digi")
# task 6
t=pd.read_csv(R+"results/sensitivity/runs.csv");L={"base":"Calibrated model","kappa_0.10":"Quality spread κ = 0.10","kappa_0.30":"Quality spread κ = 0.30","exit_0.3%":"Exits 0.3%/month","exit_1%":"Exits 1%/month","contracted_50%":"Initially contracted 50%","contracted_90%":"Initially contracted 90%","discount_17.8%":"Renewal discount 17.8%","lock_in":"Full lock-in","margin_60%":"Margin 60%"}
f,(a1,a2)=fig(1660,700,1,2,sharey=True,gridspec_kw={"width_ratios":[1.35,1]});V=list(L);Y=np.arange(len(V))
for j,o in enumerate(OPS):
    for i,v in enumerate(V):
        d=t[t.variant==v];rf=d[d.scenario=="fixed_1.00"].set_index("seed");g_=d[d.scenario==f"solo_{o}_0.90"].set_index("seed").loc[rf.index];m,lo,hi=ci((g_[f"profit_{o}"]-rf[f"profit_{o}"])/rf[f"profit_{o}"]*100)
        a1.errorbar(m,i+(j-1)*.24,xerr=[[m-lo],[hi-m]],fmt="o",ms=8,color=C[o],lw=2,label=o if i==0 else None)
for i,v in enumerate(V):
    d=t[t.variant==v];rf=d[d.scenario=="fixed_1.00"].set_index("seed");g_=d[d.scenario=="bandit"].set_index("seed").loc[rf.index];m,lo,hi=ci((g_.profit_incumbents-rf.profit_incumbents)/rf.profit_incumbents*100)
    a2.errorbar(m,i,xerr=[[m-lo],[hi-m]],fmt="o",ms=9,color=C["DIGI"],lw=2)
for a in(a1,a2):a.axvline(0,color=INK,lw=1.5);a.grid(axis="y",visible=False)
a1.set_yticks(Y,[L[v] for v in V]);a1.invert_yaxis();a1.set(xlabel="Own profit, cutting alone to ×0.90 (% vs list)");a1.legend(loc="lower center",bbox_to_anchor=(.5,1.0),ncol=3)
a2.set(xlabel="Joint profit with learned prices (% vs list)");save(f,"sensitivity")
