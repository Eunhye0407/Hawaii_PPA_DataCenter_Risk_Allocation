"""원본 ZIP → 정규화 CSV + 품질 검증. 외부 다운로드/가상 데이터 없음."""
from pathlib import Path
import csv, zipfile, io, json, collections
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'input'
OUT=ROOT/'data'/'processed'; OUT.mkdir(parents=True,exist_ok=True)
TABLES=ROOT/'outputs'/'tables';TABLES.mkdir(parents=True,exist_ok=True)
FILES={'contract_prices':('island,month,category,source,price_cents_kwh,share_of_purchased_pct',6508), 'contract_panel':('island,month,category,source,price_cents_kwh,share_of_purchased_pct,contract,fuel_cost_cents_mmbtu,regime,formula',6296),'island_month':('island,month,fuel_cost_cents_mmbtu,ecrc_cents_kwh,composite_purchased,purchased_share_of_system_pct',416)}

def read_csv_bytes(z, needle):
    for n in z.namelist():
        if n.lower().endswith('.csv'):
            s=z.read(n).decode('utf-8-sig',errors='replace')
            if s.splitlines() and s.splitlines()[0].strip()==needle:
                return n,list(csv.DictReader(io.StringIO(s)))
    raise FileNotFoundError(f'ZIP에서 열 구조를 찾지 못함: {needle}')

def writecsv(path, rows, fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    z=zipfile.ZipFile(SRC/'PPA_hedge_data.zip')
    summary=[]; data={}
    for key,(header,_) in FILES.items():
        source,rows=read_csv_bytes(z,header);data[key]=rows
        writecsv(OUT/f'{key}.csv',rows,header.split(','))
        months=[r['month'] for r in rows if r.get('month')];islands=collections.Counter(r['island'] for r in rows)
        null=sum(not r['price_cents_kwh'].strip() for r in rows) if 'price_cents_kwh' in rows[0] else None
        keycols=['island','month','source'] if key=='contract_prices' else (['island','month'] if key=='island_month' else ['island','month','source','regime'])
        duplicates=len(rows)-len(set(tuple(r.get(k,'') for k in keycols) for r in rows))
        summary.append({'dataset':key,'rows':len(rows),'start_month':min(months),'end_month':max(months),'island_counts':dict(islands),'price_nulls':null,'duplicate_keys':duplicates,'source_zip_member':source})
    # 패널은 On/Off Peak 별도 행 포함 가능; 단순 중복은 오류로 확정하지 않음.
    panel=data['contract_panel']; counts=collections.Counter(r['formula'] for r in panel)
    formula_rows=[{'formula':k,'rows':v} for k,v in sorted(counts.items())]
    writecsv(TABLES/'ppa_formula_counts.csv',formula_rows,['formula','rows'])
    writecsv(TABLES/'data_audit.csv',[{'dataset':r['dataset'],'rows':r['rows'],'first_month':r['start_month'],'last_month':r['end_month'],'islands':json.dumps(r['island_counts'],ensure_ascii=False),'price_nulls':r['price_nulls'],'duplicate_keys':r['duplicate_keys']} for r in summary],['dataset','rows','first_month','last_month','islands','price_nulls','duplicate_keys'])
    (TABLES/'audit_detail.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DATA AUDIT')
    for r in summary:print(r['dataset'],r['rows'],r['start_month'],r['end_month'],'duplicates',r['duplicate_keys'])
    print('FORMULAS',dict(counts))
    return summary
if __name__=='__main__':main()
