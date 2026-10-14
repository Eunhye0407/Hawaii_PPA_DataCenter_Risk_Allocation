# 하와이 PPA와 데이터센터 요금제의 위험 배분 및 경제적 가치

## 검증 상태
- 기존 v7 원자료 전체 재실행 및 저장 결과 차이 0: **사용자가 이전에 직접 확인한 결과**입니다. 이번 패키지의 `src/run_all.py`는 PPA 회귀 자체를 다시 추정하지 않습니다. 이를 구분합니다.
- 새 코드에서 데이터셋 검증과 AEP DCT 가상 계약 시나리오를 실제 실행했습니다.
- AEP의 100MW 단계별 최소 청구 용량은 ramp 종료 후 **82.5 MW**입니다.
- 시나리오용 임의 가정은 계약용량 100 MW, 최대수요 활성용량의 80%, 수요요금 $10/kW-월, 12년 계약입니다.

## 핵심 자료
- `PPA_DataCenter_Risk_Allocation_Research_Brief.pdf` / `PPA_DataCenter_Analysis_Results.xlsx`
- `outputs/tables/dct_monthly_scenarios.csv`, `dct_summary.csv`, `assumptions.json`
- `data/prior_results/`: v7 재현 결과. 특히 `fair_price.csv`, `hedge_risk.csv`, `hedge_decomposition.csv`.
- `src/02_tariff_stress_test.py` : AEP 공식 구간별 요금·ramp 최소 청구 함수.

## 수치 해석
- 이번 12년 시나리오 수치는 사용자 제시 3.3/12.3/11.1/29.1m와 다릅니다. 기간·최대수요·조기종료 기준의 차이로 해석되므로 동일 결과라고 주장하지 않습니다.
- 초기 철수 사례는 **계약이 유지될 때의 의무**로 가정하였고, 9년 경과 후의 선택적 해지(36개월분)는 적용하지 않았습니다.
- 수요요금만 가정적으로 계산합니다. 에너지 요금·승인된 실제 전압별 요율·리이더·투자비·수금확률·할인율은 미포함입니다.
- Wailuku $176.7은 가격 수준 효과이지 보험금이 아닙니다.
- 유가 반응 p=0.036은 가격 공식 군집 3개만 있어서 통계적 추론에 주의가 필요합니다.

## 출처
- AEP https://www.aepohio.com/company/about/rates/data-center-tariff/
- EPRI 2026 Powering Intelligence, 보고서 pp.14-15
- 사용자 제공 PPA v7 코드/결과 및 HELCO 공시

## 재실행
`python src/run_all.py`
