"""실제 PPA 정규화 데이터 + 별도 명시한 예시 시나리오로 그림 생성."""
from pathlib import Path
import csv,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'outputs'/'figures';FIG.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'processed';TABLES=ROOT/'outputs'/'tables'
plt.rcParams.update({'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})

def rows(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    panel=rows(DATA/'contract_panel.csv')
    contracts=['Hawi Renewable Dev.','Wailuku Hydro','PGV','Tawhiri (Pakini Nui)']
    fig,ax=plt.subplots(figsize=(10.5,4.8))
    for c in contracts:
        bymonth=collections.defaultdict(list)
        for r in panel:
            if r['island']=='hawaii' and r['contract']==c and r['price_cents_kwh']:
                v=float(r['price_cents_kwh'])
                if v>0:bymonth[r['month']].append(v)
        xs=sorted(bymonth)
        ax.plot(xs,[sum(bymonth[x])/len(bymonth[x]) for x in xs],label=c,linewidth=1.5)
    ax.set_xticks(list(range(0,145,24)));ax.set_xticklabels([f'{2015+i//12}' for i in range(0,145,24)])
    ax.set_ylabel('Published contract price (US cents/kWh)');ax.set_xlabel('Month (starting Jan 2015)')
    ax.set_title('Hawaii Island — published PPA prices (original contract panel)',loc='left')
    ax.legend(loc='upper left',fontsize=8);fig.tight_layout();fig.savefig(FIG/'01_ppa_prices.png');plt.close(fig)
    s=rows(TABLES/'dct_summary.csv')
    fig,ax=plt.subplots(figsize=(9.4,4.7))
    labels=[r['scenario'] for r in s]
    vals=[float(r['minimum_topup_vs_peak_usd'])/1e6 for r in s]
    ax.bar(labels,vals)
    ax.set_ylabel('12-year minimum billing top-up ($ million)')
    ax.set_title('Illustrative AEP DCT ramp + 82.5MW post-ramp floor; 100MW, $10/kW-month',loc='left')
    ax.tick_params(axis='x',rotation=12)
    fig.tight_layout();fig.savefig(FIG/'02_tariff_illustrative.png');plt.close(fig)
    print('FIGURES CREATED',sorted(p.name for p in FIG.glob('*.png')))
if __name__=='__main__':main()
