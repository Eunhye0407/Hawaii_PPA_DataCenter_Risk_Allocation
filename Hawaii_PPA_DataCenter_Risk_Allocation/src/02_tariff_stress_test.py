"""AEP Ohio Schedule DCT based, explicitly illustrative demand-charge stress test.
The hypothetical $10/kW-month is NOT AEP approved rate. No energy, riders, collateral
cash flow, discounting or real ratepayer incidence included. All trajectories are
stress tests, not forecasts or probabilities.
Sources: https://www.aepohio.com/company/about/rates/data-center-tariff/
"""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'tables';OUT.mkdir(parents=True,exist_ok=True)
CONTRACT_MW=100.0
RATE=10.0
PEAK_UTIL=0.8 # EPRI empirical peak ~0.80 for illustrated hyperscale site; sensitivity required
RAMP_CAPACITY=[0.50,0.65,0.80,0.90]
ACTIVE={'normal':[0.2,0.4,0.6,0.8]+[1.0]*8,'delay':[0,0.2,0.4,0.6,0.8]+[1.0]*7,'partial':[0.2,0.4]+[0.5]*10,'cease_after_2y':[0.2,0.4]+[0.0]*10}

def schedule_minimum_mw(capacity_mw):
    """Schedule DCT tiered minimum, applying explicit 85% ceiling."""
    if capacity_mw<=25: return 0.0
    if capacity_mw<=75: demand=15+.85*(capacity_mw-25)
    else: demand=57.5+(capacity_mw-75)
    return min(demand,.85*capacity_mw)

def simulate(name,actives):
    hist=[]; output=[]
    for year,active in enumerate(actives,1):
        peak=CONTRACT_MW*active*PEAK_UTIL
        for month in range(1,13):
            if year<=4:
                # During ramp: >=85% of year's load-ramp contract capacity
                contractual_floor=.85*CONTRACT_MW*RAMP_CAPACITY[year-1]
                past_floor=0.0
            else:
                contractual_floor=schedule_minimum_mw(CONTRACT_MW)
                past_floor=.85*max(hist[-11:]) if hist else 0.0
            billed=max(peak,contractual_floor,past_floor)
            topup=max(0,billed-peak)*1000*RATE
            output.append({'scenario':name,'year':year,'month':month,'active_fraction':active,'assumed_peak_mw':round(peak,4),'ramp_floor_mw':round(contractual_floor,4),'historical_11_month_floor_mw':round(past_floor,4),'billed_demand_mw':round(billed,4),'monthly_charges_usd':round(billed*1000*RATE,2),'monthly_minimum_topup_usd':round(topup,2)})
            hist.append(billed) # previous monthly BILLING DEMAND vs peak: methodology note
    return output

def main():
    allrows=[]; sums=[]
    for scenario,active in ACTIVE.items():
        rows=simulate(scenario,active);allrows+=rows
        sums.append({'scenario':scenario,'years':12,'total_demand_charge_usd':round(sum(x['monthly_charges_usd'] for x in rows),2),'minimum_topup_vs_peak_usd':round(sum(x['monthly_minimum_topup_usd'] for x in rows),2),'annual_early_year_1_topup_usd':round(sum(x['monthly_minimum_topup_usd'] for x in rows if x['year']==1),2),'peak_utilization_assumption':PEAK_UTIL})
    for file,rows in [('dct_monthly_scenarios.csv',allrows),('dct_summary.csv',sums)]:
        with (OUT/file).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    (OUT/'assumptions.json').write_text(json.dumps({'contract_MW':CONTRACT_MW,'illustrative_demand_charge_USD_per_kW_month':RATE,'peak_utilization':PEAK_UTIL,'load_ramp_capacities':RAMP_CAPACITY,'after_ramp_tiered_minimum_MW':schedule_minimum_mw(CONTRACT_MW),'billing':'monthly 30-min peak vs 85% ramp capacity during ramp; afterwards max(tier min, 85% preceding 11-month highest billing demand, observed peak)','term_years':12,'early_shutdown':'obligation simulated through initial term; NOT a permitted 36-month exit; stop month-year 3','limitations':'No energy charges, approved primary/secondary rate, riders, exit option, changing prices, capacity reassignment, collateral utilization, discounting, capital recovery; 11-month rule interpreted from billed peak; sensitivity needed'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('AEP DCT 100MW TIER MIN =',schedule_minimum_mw(100),'MW')
    for r in sums:print(r)
    return sums
if __name__=='__main__':main()
