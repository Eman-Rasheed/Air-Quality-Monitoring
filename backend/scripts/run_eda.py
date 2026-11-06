from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine
BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from app.config import DB, POLLUTANTS, REPORTS
REPORTS.mkdir(parents=True,exist_ok=True)
if not DB.exists(): raise SystemExit("Database missing. Run API/ETL first.")
engine=create_engine(f"sqlite:///{DB.as_posix()}")
with engine.connect() as conn: df=pd.read_sql_query("SELECT * FROM air_quality_records",conn)
if df.empty: raise SystemExit("No records. Run ETL first.")
df["timestamp"]=pd.to_datetime(df.timestamp,errors="coerce")
df[POLLUTANTS]=df[POLLUTANTS].apply(pd.to_numeric,errors="coerce")
sns.set_theme(style="whitegrid")
means=df.groupby("city")[POLLUTANTS].mean()
means.to_csv(REPORTS/"city_pollutant_means.csv")
means.plot(kind="bar",figsize=(13,7)); plt.title("Mean Pollutant Concentrations by City")
plt.ylabel("Concentration (API units)"); plt.tight_layout(); plt.savefig(REPORTS/"city_comparison.png",dpi=160); plt.close()
df["hour"]=df.timestamp.dt.hour
hourly=df.groupby("hour")[POLLUTANTS].mean()
hourly.to_csv(REPORTS/"hourly_means.csv")
hourly.plot(figsize=(13,7),marker="o"); plt.title("Hourly Pollutant Trends")
plt.xlabel("Hour of day"); plt.ylabel("Concentration (API units)"); plt.xticks(range(24))
plt.tight_layout(); plt.savefig(REPORTS/"hourly_trends.png",dpi=160); plt.close()
plt.figure(figsize=(9,7)); sns.heatmap(df[POLLUTANTS].corr(),annot=True,cmap="coolwarm",vmin=-1,vmax=1,fmt=".2f")
plt.title("Pollutant Correlation Heatmap"); plt.tight_layout(); plt.savefig(REPORTS/"correlation_heatmap.png",dpi=160); plt.close()
long=df.melt(id_vars=["city"],value_vars=POLLUTANTS,var_name="pollutant",value_name="concentration")
plt.figure(figsize=(14,7)); sns.boxplot(data=long,x="pollutant",y="concentration",hue="city")
plt.title("Pollutant Distributions and Potential Outliers"); plt.tight_layout()
plt.savefig(REPORTS/"outlier_boxplots.png",dpi=160); plt.close()
df.groupby("city")[POLLUTANTS].agg(["count","mean","median","std","min","max"]).to_csv(REPORTS/"descriptive_statistics.csv")
out=[]
for city,g in df.groupby("city"):
    for p in POLLUTANTS:
        s=g[p].dropna()
        if len(s):
            q1,q3=s.quantile([.25,.75]); iqr=q3-q1
            out.append({"city":city,"pollutant":p,"iqr_outliers":int(((s<q1-1.5*iqr)|(s>q3+1.5*iqr)).sum())})
pd.DataFrame(out).to_csv(REPORTS/"iqr_outlier_counts.csv",index=False)
print("EDA reports created at",REPORTS)
