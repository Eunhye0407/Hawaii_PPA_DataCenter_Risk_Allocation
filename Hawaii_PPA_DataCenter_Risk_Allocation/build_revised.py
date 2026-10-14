from pathlib import Path
import csv,zipfile
from artifact_tool import Workbook,SpreadsheetFile
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
R=Path(__file__).resolve().parent;T=R/'outputs'/'tables';O=R/'data'/'prior_results'
def csvrows(p):
 with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.reader(f))
wb=Workbook.create()
sections=[('Overview',[['항목','상태/값','의미'],['PPA v7 CSV 원본 재현','사용자 검증: 저장 결과와 차이 0','독립 재실행은 이전 세션에서 사용자 수행; 이 패키지 실행은 검증표 재생성'],['PPA 분석 패널',6296,'월별 계약 패널'],['Hawi 고정계약 가격 (¢/kWh)',15.5,'실제 공시 가격'],['Hawi 공정가격 (¢/kWh)',16.0,'2015~2026 사후 평균에 의한 추정; 계약시점 사전공정가격과 구분'],['Hawi 500kWh 손익 하위5% ($)',-13.904427869019196,'기존 hedge_risk.csv VaR5'],['Hawi 500kWh 손익 상위5% ($)',17.064313762016923,'기존 hedge_risk.csv VaR95'],['Wailuku 500kWh 누적 손익 ($)',176.7,'공정가격과 실제 계약가격 수준 차이, 보험금으로 지칭 금지'],['AEP 100MW 계약 최저 청구 용량 (MW)',82.5,'증가 유예 종료 후 해당 구간; 85MW 일률 적용 금지'],['실제 청구 단가','시나리오 $10/kW-월','공식 AEP 승인 요금이 아님'],['추가금액의 의미','최소 청구에 의한 청구 증가','실제 수금, 전력회사 순편익 또는 소비자 절감액 아님']]),('PPA FE reproduced',csvrows(O/'panel_fe_results.csv')),('PPA fair price',csvrows(O/'fair_price.csv')),('PPA risk',csvrows(O/'hedge_risk.csv')),('PPA decomposition',csvrows(O/'hedge_decomposition.csv')),('DCT scenarios',csvrows(T/'dct_summary.csv')),('DCT monthly',csvrows(T/'dct_monthly_scenarios.csv')),('Audit',csvrows(T/'data_audit.csv'))]
for name,rows in sections:
 s=wb.worksheets.add(name)
 if name!='Overview':
  for i,row in enumerate(rows[1:],1):
   for j,v in enumerate(row):
    try: rows[i][j]=float(v) if v and v.replace('.','',1).replace('-','',1).isdigit() else v
    except: pass
 maxlen=max(map(len,rows));rows=[r+['']*(maxlen-len(r)) for r in rows]
 s.get_range_by_indexes(0,0,len(rows),maxlen).values=rows
 s.get_range_by_indexes(0,0,1,maxlen).format={'fill':'#15324D','font':{'bold':True,'color':'#FFFFFF'},'row_height':29}
 s.get_range_by_indexes(0,0,len(rows),maxlen).format.column_width=25
 s.get_range('A:A').format.column_width=37
 if name=='Overview':s.get_range('B:B').format.column_width=46;s.get_range('C:C').format.column_width=87
 s.freeze_panes.freeze_rows(1)
SpreadsheetFile.export_xlsx(wb).save(str(R/'PPA_DataCenter_Analysis_Results.xlsx'))
font='/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf';fontb='/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf'
pdfmetrics.registerFont(TTFont('Nanum',font));pdfmetrics.registerFont(TTFont('NanumB',fontb))
c=canvas.Canvas(str(R/'PPA_DataCenter_Risk_Allocation_Research_Brief.pdf'),pagesize=(595,842))
NAVY=HexColor('#122F4A');SUB=HexColor('#40536A');TEAL=HexColor('#007C80')
def t(y,x,text,size=10,bold=False,color=NAVY):
 c.setFont('NanumB' if bold else 'Nanum',size);c.setFillColor(color);c.drawString(x,y,text)
def lines(y,content,size=9.5,gap=20):
 for ln in content:t(y,47,ln,size);y-=gap
 return y
def head(page,heading):
 t(800,45,'하와이 PPA와 데이터센터 요금제의 위험 배분 및 경제적 가치',13,True)
 t(772,45,heading,10,True,TEAL);c.setStrokeColor(HexColor('#CBD5E1'));c.line(45,756,550,756)
 c.line(45,44,550,44);t(27,45,'2026.10 | 실제 자료 / 사용자 재현 보고 / 가정 시뮬레이션 구분',8,color=SUB);t(27,535,str(page),9)
head(1,'1 | PPA 핵심 결과와 재현 상태')
t(723,47,'연구 중심 질문',12,True)
lines(699,['계약 가격 구조가 연료가격 충격을 누구에게 이전하며, 그 경제적 가치는 얼마인가?'])
t(658,47,'기존 v7 PPA 결과의 재현 상태',12,True)
lines(634,['사용자는 v7 노트북을 원자료 CSV로 처음부터 재실행하여 저장 결과와 차이 0을 확인했습니다.','본 수정 패키지에는 해당 결과 파일을 보존했습니다. (본 세션 자체 재추정 인증과는 구분)'])
t(561,47,'PPA 계약의 경제적 위험 배분 결과',12,True)
lines(536,['Hawi: 실제 고정가 15.5¢/kWh, 사후 공정 고정가격 16.0¢/kWh.','500kWh 가구 12개월 손익: 하위 5% −$13.90, 상위 5% +$17.06.','Wailuku: 500kWh 환산 손익 +$176.7 — 고정가 보험금이 아닌 낮은 재계약 가격 효과.'])
t(420,47,'유가 반응 계수 (기존 v7 재현 결과)',12,True)
lines(397,['빠른 연동(재생) 0.557, wild-bootstrap p=0.036, 처치 가격 공식 3개.','유가 연동(화석) 0.728, p=0.015, 공식 4개. 느린 연동 0.006, p=0.543.','공식 수가 적어 특히 p=0.036은 민감함. 개별 공식 추정 범위 별도 검증 필요.'])
t(288,47,'주의: 사후 공정가격 ≠ 계약 체결 당시 공정가격',11,True)
lines(266,['2015~2026년 실현가격으로 계산한 공정 고정가는 사후적 벤치마크입니다.','이를 계약 당시의 기대보험료로 해석하지 않도록 구분해 보고합니다.'])
head_unused=0;c.showPage()
head(2,'2 | AEP 공식 DCT 계약 조건에 근거한 수정 시뮬레이션')
t(722,47,'공식 근거: AEP Ohio Schedule DCT · 2025-07-23 발효',11,True)
lines(699,['25MW 초과 대상. 4년 ramp (50·65·80·90%), 이후 8년 계약 의무.','100MW 계약 최소수요: 57.5MW + (100−75)MW = 82.5MW (최대 85% 상한).','ramp 중 청구수요 하한: 해당 연도 ramp 계약용량의 85%.','ramp 이후: 구간별 최소수요와 직전 11개월 최고 청구수요 85% 중 큰 값.'])
t(582,47,'시나리오별 최소 청구 추가액: 12년 합계 / $백만',11,True)
from PIL import Image
c.drawImage(str(R/'outputs'/'figures'/'02_tariff_illustrative.png'),48,270,width=500,height=290,preserveAspectRatio=True,anchor='c')
rows=csvrows(T/'dct_summary.csv')
for i,row in enumerate(rows[1:]):t(251-i*19,52,f'{row[0]}  :  ${float(row[3])/1e6:,.2f}m',9.5)
t(156,47,'중요한 가정과 해석',11,True)
lines(136,['100MW, 월 $10/kW 수요요금, 최대수요=활성용량×80%: 모두 명시적 가정.','청구액의 추가분이지 순보험가치/가구 요금 절감이 아닙니다.','제시받은 3.3·12.3·11.1·29.1m와는 기간·부하·해지 가정 차이로 일치하지 않습니다.'],8.6,17)
c.showPage()
head(3,'3 | 추가 확인과 논문 반영 원칙')
t(717,47,'근거 및 데이터 상태',12,True)
lines(695,['AEP 공식 안내: https://www.aepohio.com/company/about/rates/data-center-tariff/','AEP Schedule DCT: 월 30분 통합 최대수요, 계약 용량 구간별 최소 청구.','EPRI Powering Intelligence 2026 (보고서 내부 pp.14~15): 부하 증가와 최대 이용률.','v7 저장 결과: panel_fe_results, fair_price, hedge_decomposition, hedge_risk CSV.'])
t(586,47,'남은 핵심 검증',12,True)
lines(565,['① user가 제시한 네 가지 시나리오 수치에 사용된 전체 코드·정의 확인','② AEP 요금표 내 전압별 실제 수요요금·리이더·지불 의무 및 해지 별도 구현','③ 부하수요 월 최대값과 에너지 사용량(부하율)의 단위·자료 출처 분리','④ PPA v7 연구용 추론과 사전 공정가격의 의미 및 오류 검증','⑤ 기존 고객 비용 전가를 주장하려면 실제 투자비·비용 회수 분석 추가'])
t(433,47,'발표 메시지',12,True)
lines(408,['IEEE: PPA 실증계수·실제 보험가치 및 두 위험의 분석 틀','Eastern Builders: AEP의 최소 청구·철수/부하 축소 조건과 기업 부담','EPS: 하와이 계통에서 가상 대형 부하를 받을 때의 비용 회수 시사점'])
t(318,47,'현재 주장 가능한 것 / 아직 주장할 수 없는 것',12,True)
lines(294,['가능: 원자료 현황, 기존 v7 재현 결과(사용자 확인), AEP 공식 계약 보호 조항,','      조건을 명시한 12년 계약의 수요요금 추가 청구 시나리오.','불가: 이 금액이 실제 전력회사 순수익·실제 투자비 절감·주택 요금 인하라는 주장.'])
t(181,47,'파일 실행: python src/run_all.py',10,True,TEAL)
c.save()
readme=R/'README.md';readme.write_text('''# 하와이 PPA와 데이터센터 요금제의 위험 배분 및 경제적 가치\n\n## 검증 상태\n- 기존 v7 원자료 전체 재실행 및 저장 결과 차이 0: **사용자가 이전에 직접 확인한 결과**입니다. 이번 패키지의 `src/run_all.py`는 PPA 회귀 자체를 다시 추정하지 않습니다. 이를 구분합니다.\n- 새 코드에서 데이터셋 검증과 AEP DCT 가상 계약 시나리오를 실제 실행했습니다.\n- AEP의 100MW 단계별 최소 청구 용량은 ramp 종료 후 **82.5 MW**입니다.\n- 시나리오용 임의 가정은 계약용량 100 MW, 최대수요 활성용량의 80%, 수요요금 $10/kW-월, 12년 계약입니다.\n\n## 핵심 자료\n- `PPA_DataCenter_Risk_Allocation_Research_Brief.pdf` / `PPA_DataCenter_Analysis_Results.xlsx`\n- `outputs/tables/dct_monthly_scenarios.csv`, `dct_summary.csv`, `assumptions.json`\n- `data/prior_results/`: v7 재현 결과. 특히 `fair_price.csv`, `hedge_risk.csv`, `hedge_decomposition.csv`.\n- `src/02_tariff_stress_test.py` : AEP 공식 구간별 요금·ramp 최소 청구 함수.\n\n## 수치 해석\n- 이번 12년 시나리오 수치는 사용자 제시 3.3/12.3/11.1/29.1m와 다릅니다. 기간·최대수요·조기종료 기준의 차이로 해석되므로 동일 결과라고 주장하지 않습니다.\n- 초기 철수 사례는 **계약이 유지될 때의 의무**로 가정하였고, 9년 경과 후의 선택적 해지(36개월분)는 적용하지 않았습니다.\n- 수요요금만 가정적으로 계산합니다. 에너지 요금·승인된 실제 전압별 요율·리이더·투자비·수금확률·할인율은 미포함입니다.\n- Wailuku $176.7은 가격 수준 효과이지 보험금이 아닙니다.\n- 유가 반응 p=0.036은 가격 공식 군집 3개만 있어서 통계적 추론에 주의가 필요합니다.\n\n## 출처\n- AEP https://www.aepohio.com/company/about/rates/data-center-tariff/\n- EPRI 2026 Powering Intelligence, 보고서 pp.14-15\n- 사용자 제공 PPA v7 코드/결과 및 HELCO 공시\n\n## 재실행\n`python src/run_all.py`\n''',encoding='utf-8')
print('built',R/'PPA_DataCenter_Analysis_Results.xlsx',R/'PPA_DataCenter_Risk_Allocation_Research_Brief.pdf')
