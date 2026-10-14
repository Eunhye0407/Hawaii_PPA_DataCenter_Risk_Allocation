# %% [markdown]
# # 섬 전력망의 연료가격 보험 — 제안서 v7 분석 노트북
#
# 제안서 v7의 분석을 **데이터셋 CSV만으로** 처음부터 끝까지 다시 돌리는 노트북입니다.
# 위에서부터 셀을 순서대로 실행하면 표와 그림이 나오고, `outputs/` 폴더에 저장됩니다.
#
# | 절 | 분석 | 제안서 위치 |
# |---|---|---|
# | 1 | 데이터 한눈에 보기 | 2장 |
# | 2 | 유가 충격 자동 탐지 | 6장-3 |
# | 3 | **메인 ①** 계약 패널: 계약 방식별 유가 전가율 | 6장-1 |
# | 4 | **메인 ②** 보험 평가: 보험료·보험금, 공정 고정가, 최악·최선 5% | 6장-2 |
# | 5 | 유가 연동 계약이 하와이섬 요금에 더한 몫 (2019~2026) | 7장 |
# | 6 | 보조: PGV 발전소 안 비교, 고정가 전환 이벤트 스터디·위약 | 6장-4 |
# | 7 | 저장된 결과표(04_results)와 대조 | — |
#
# **준비물**: 이 노트북과 같은 폴더에 `island_ppa_dataset/` 폴더(압축 푼 것)를 두세요.
# 필요한 패키지: `pandas numpy statsmodels matplotlib` (Colab에는 기본 설치되어 있음)

# %%
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

# ---- 경로: 데이터셋 폴더 위치가 다르면 여기만 고치면 됩니다
DATA = Path("island_ppa_dataset")
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)
assert (DATA / "03_analysis_panel" / "contract_panel.csv").exists(), "DATA 경로를 확인하세요"

# ---- 한글 폰트 (Windows 맑은 고딕 / Mac 애플고딕 / 리눅스·Colab 노토)
def set_korean_font():
    names = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]
    have = {f.name for f in fm.fontManager.ttflist}
    for n in names:
        if n in have:
            plt.rcParams["font.family"] = n
            break
    else:
        for f in fm.findSystemFonts():
            if "NotoSansCJK" in f or "NanumGothic" in f:
                fm.fontManager.addfont(f)
                plt.rcParams["font.family"] = fm.FontProperties(fname=f).get_name()
                break
    plt.rcParams["axes.unicode_minus"] = False
set_korean_font()
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})

# ---- 공통 상수
LF, RT = 1.062, 1.0975          # 하와이섬 연료비 조정요금 환산: 손실계수 × 세금 승수
HH_KWH = 500                    # 대표 가구 월 사용량 (kWh) → ¢/kWh × 500 / 100 = $ → ×5
SWITCH = {"Hawi Renewable Dev.": "2023-09", "Wailuku Hydro": "2025-06"}   # 고정가 전환 시점
COL = {"fix": "#2b6cb0", "fast": "#dd6b20", "slow": "#38a169", "fos": "#718096", "up": "#e53e3e", "down": "#3182ce"}
print("준비 완료")

# %% [markdown]
# ## 1. 데이터 불러오기와 한눈에 보기
#
# - `contract_panel.csv`: 계약×월 단가 (2015~2026, 오아후·하와이섬·마우이). `formula` 열이 가격 방식입니다.
# - 브렌트유: FRED 월평균
# - 하와이섬 월별 공시값: 구매전력 비중 등 (요금 환산에 사용)

# %%
panel = pd.read_csv(DATA / "03_analysis_panel/contract_panel.csv")
classif = pd.read_csv(DATA / "03_analysis_panel/contract_classification.csv")

b = pd.read_csv(DATA / "02_external/brent_monthly_fred.csv")
b["month"] = b.observation_date.str[:7]
brent = b.set_index("month").MCOILBRENTEU.sort_index()

isl = pd.concat([pd.read_csv(DATA / "01_extracted_from_pdf/hawaii_ecr_island_month_2015_2018.csv"),
                 pd.read_csv(DATA / "01_extracted_from_pdf/hawaii_ecr_island_month.csv")])
hi = isl[isl.island == "hawaii"].drop_duplicates("month").set_index("month").sort_index()

print(f"계약×월 행: {len(panel):,}  |  기간 {panel.month.min()} ~ {panel.month.max()}")
print("\n가격 방식별 계약(×전환 구간) 수:")
print(classif.groupby(["formula", "island"]).size().unstack(fill_value=0))

# %%
# 그림 1: 같은 단가표를 쓰던 세 계약 + 느린 연동 + 브렌트유
h = panel[(panel.island == "hawaii") & (panel.price_cents_kwh > 0)]
pv = h.groupby(["contract", "month"]).price_cents_kwh.mean().unstack(0)
fig, ax = plt.subplots(figsize=(11, 4.6))
x = pd.to_datetime(pv.index)
ax.plot(x, pv["PGV"], color=COL["fast"], lw=2.4, label="PGV 지열 (계속 유가 연동)")
ax.plot(x, pv["Hawi Renewable Dev."], color=COL["fix"], lw=1.6, ls="--", label="Hawi 풍력 (2023.9 고정가 15.5¢)")
ax.plot(x, pv["Wailuku Hydro"], color="#805ad5", lw=1.6, ls=":", label="Wailuku 수력 (2025.6 고정가 7¢)")
ax.plot(x, pv["Tawhiri (Pakini Nui)"], color=COL["slow"], lw=1.6, label="Pakini Nui 풍력 (느린 연동)")
ax.set_ylabel("구매단가 (¢/kWh)")
ax2 = ax.twinx(); ax2.grid(False)
bx = brent.loc[pv.index.min():pv.index.max()]
ax2.plot(pd.to_datetime(bx.index), bx, color="k", lw=0.9, alpha=0.45, label="브렌트유 (오른쪽, $/배럴)")
ax2.set_ylabel("브렌트유 ($/배럴)")
for k, v in SWITCH.items():
    ax.axvline(pd.to_datetime(v), color="#c53030", lw=0.8, ls="--")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left", ncol=2)
ax.set_title("그림 1. 하와이섬 재생 계약 단가: 같은 단가표에서 두 계약만 고정가로", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig1_contracts.png", dpi=150); plt.show()

diff = (pv.loc[:"2023-08", "Hawi Renewable Dev."] - pv.loc[:"2023-08", "PGV"]).abs()
print(f"전환 전 {diff.notna().sum()}개월 중 Hawi와 PGV 단가가 다른 달: {(diff > 1e-6).sum()}개월 → {list(diff[diff > 1e-6].index)}")
print("  (2016-06은 PGV의 On Peak 값이 공시 추출에서 빠져 Off Peak만 평균된 것. 원본 PDF 확인 필요)")
pgv_share = panel[(panel.island == "hawaii") & (panel.contract == "PGV")].groupby("month").share_of_purchased_pct.sum()
off = pgv_share[pgv_share == 0]
print(f"PGV 구매비중 0인 달(2018 화산 분화로 가동 중단): {off.index.min()} ~ {off.index.max()}, {len(off)}개월 — 단가는 계속 공시됨")

# %% [markdown]
# ## 2. 유가 충격 자동 탐지 (제안서 6장-3)
#
# 규칙: 브렌트유가 **직전 24개월 중앙값**에서 로그로 **T 이상** 벗어난 달 = 충격.
# T는 분석 기간 밖(1990~2014) 유가 편차의 1 표준편차로 정합니다. 연구자가 연도를 고르지 않게 하려는 장치입니다.
# 3개월 이하 공백은 이어 붙이고, 2개월 미만 구간은 버립니다.

# %%
def detect_shocks(W=24, T=0.25, start="2015-01"):
    base = brent.rolling(W, min_periods=W // 2).median().shift(1)   # 과거 값만 사용
    dev = np.log(brent / base)
    flag = (dev.abs() > T) & (dev.index >= start)
    sign = np.sign(dev).where(flag, 0)
    idx = list(dev.index); wins, cur = [], None
    for i, m in enumerate(idx):
        if sign.iloc[i] != 0:
            if cur and cur["sign"] == sign.iloc[i] and i - cur["last_i"] <= 4:
                cur["end"], cur["last_i"] = m, i
            else:
                if cur: wins.append(cur)
                cur = dict(start=m, end=m, sign=sign.iloc[i], last_i=i)
    if cur: wins.append(cur)
    rows = []
    for w in wins:
        n = idx.index(w["end"]) - idx.index(w["start"]) + 1
        if n >= 2:
            seg = dev.loc[w["start"]:w["end"]]
            rows.append(dict(W=W, T=T, start=w["start"], end=w["end"], months=n,
                             type="급등" if w["sign"] > 0 else "폭락",
                             peak_dev=round(seg.abs().max() * np.sign(w["sign"]), 2)))
    return pd.DataFrame(rows), dev

_base = brent.rolling(24, min_periods=12).median().shift(1)
T_MAIN = round(float(np.log(brent / _base).loc["1990-01":"2014-12"].std()), 2)
shocks, dev = detect_shocks(24, T_MAIN)
print(f"기준 T = {T_MAIN} (1990~2014 편차의 1 표준편차)\n")
print(shocks.to_string(index=False))

def shock_label(m):
    for r in shocks.itertuples():
        if r.start <= m <= r.end:
            yr = r.start[:4] if r.start[:4] == r.end[:4] else f"{r.start[:4]}~{r.end[2:4]}"
            return f"{yr} {r.type}"
    return "평상시"

# 민감도: 창 길이 W와 기준 T를 바꿔도 같은 구간이 나오나
sens = pd.concat([detect_shocks(W, T)[0] for W in (12, 24, 36) for T in (0.20, 0.25, 0.30)])
print("\n== 민감도: 설정별 탐지 구간 ==")
print(sens.groupby(["W", "T"]).apply(lambda d: ", ".join(f"{r.start}~{r.end}{r.type}" for r in d.itertuples())).to_string())
shocks.to_csv(OUT / "shock_windows.csv", index=False)

# %%
fig, ax = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw=dict(height_ratios=[1.3, 1]))
bx = brent.loc["2013-01":]
ax[0].plot(pd.to_datetime(bx.index), bx, color="k", lw=1.5)
ax[1].plot(pd.to_datetime(dev.loc["2013-01":].index), dev.loc["2013-01":], color="#4a5568", lw=1.2)
ax[1].axhline(T_MAIN, color=COL["up"], ls="--", lw=1); ax[1].axhline(-T_MAIN, color=COL["down"], ls="--", lw=1)
for r in shocks.itertuples():
    c = COL["up"] if r.type == "급등" else COL["down"]
    for a in ax:
        a.axvspan(pd.to_datetime(r.start), pd.to_datetime(r.end) + pd.offsets.MonthEnd(0), color=c, alpha=0.13, lw=0)
    ax[0].text(pd.to_datetime(r.start), 128, shock_label(r.start), fontsize=8.5, color=c)
ax[0].set_ylim(10, 140); ax[0].set_ylabel("브렌트유 ($/배럴)")
ax[1].set_ylabel("직전 24개월 중앙값\n대비 로그 편차")
ax[0].set_title("그림 2. 데이터가 자동으로 찾은 유가 충격 5개 (빨강 급등, 파랑 폭락)", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig2_shocks.png", dpi=150); plt.show()

# %% [markdown]
# ## 3. 메인 ① 계약 패널: 계약 방식별 유가 전가율
#
# $$\Delta \ln p_{it} = \alpha_i + \lambda_t + \sum_{g}\sum_{L=0}^{3} \beta_{gL}\,(\Delta\ln \text{Brent}_{t-L}\times 1\{g\}) + \gamma_g\,1\{\text{1월}\}\times 1\{g\} + \varepsilon_{it}$$
#
# - **월 고정효과 λ_t**가 그 달 모든 계약이 함께 받는 충격을 걸러내므로, β는 "고정가 계약 대비 **몇 %p 더** 유가를 넘기나"입니다.
# - 기준 유형 = 고정가(고정 + 매년 1월 인상). 1월 인상은 따로 통제합니다.
# - 같은 단가표를 쓰는 계약은 독립이 아니므로 **가격 공식 단위로 군집** 표준오차를 쓰고,
#   군집이 적어 **와일드 클러스터 부트스트랩**(6점 가중치, 귀무가설 제약, 999회)으로 p값을 구합니다.

# %%
GROUP = {"FIXED_FLAT": "FIX", "FIXED_ESCALATOR": "FIX", "OIL_INDEXED": "REN",
         "FOSSIL_INDEXED": "FOS", "LAGGED_INDEXED": "LAG"}
GNAME = {"REN": "빠른 연동(재생)", "FOS": "유가 연동(화석)", "LAG": "느린 연동"}
p = panel[panel.formula.isin(GROUP) & (panel.price_cents_kwh > 0)].copy()
p["g"] = p.formula.map(GROUP)
# 연말 정산성 이상치 제거: 같은 계약 중앙값의 50% 미만
p = p[p.price_cents_kwh >= 0.5 * p.groupby(["island", "source", "regime"]).price_cents_kwh.transform("median")]
p = p.groupby(["island", "contract", "regime", "g", "month"], as_index=False).price_cents_kwh.mean()   # On/Off Peak 평균
p["unit"] = p.island + "|" + p.contract + "|" + p.regime

def formula_cluster(r):
    c, i = r.contract, r.island
    if i == "hawaii" and (c in ["PGV", "Small Hydro (>100 KW)", "Sch Q Hydro (<100 KW)"]
                          or (c in SWITCH and r.regime == "before")):
        return "하와이섬 회피비용 단가표"
    if i == "maui" and c in ["Hydro & Other", "HC&S - Unscheduled"]: return "마우이 회피비용 단가표"
    if i == "oahu" and c in ["Chevron", "IES Downstream"]: return "오아후 정유(IES/Chevron)"
    if i == "oahu" and c in ["PAR Hawaii", "THC"]: return "오아후 정유(PAR/Tesoro)"
    return r.unit
p["fcl"] = p.apply(formula_cluster, axis=1)

db = np.log(brent).diff()
p = p.sort_values(["unit", "month"])
p["y"] = p.groupby("unit").price_cents_kwh.transform(lambda s: np.log(s).diff())
p["gap"] = (pd.to_datetime(p.month) - pd.to_datetime(p.groupby("unit").month.shift())).dt.days
for L in range(4):
    p[f"d{L}"] = p.month.map(db.shift(L))
p = p[p.gap <= 31].dropna(subset=["y"] + [f"d{L}" for L in range(4)])
p = p[p.month <= "2026-09"]
p["jan"] = p.month.str.endswith("-01").astype(float)

GS = ["REN", "FOS", "LAG"]
cols = []
for g in GS:
    for L in range(4):
        p[f"{g}_{L}"] = p[f"d{L}"] * (p.g == g); cols.append(f"{g}_{L}")
for g in ["FIX"] + GS:
    p[f"jan_{g}"] = p.jan * (p.g == g); cols.append(f"jan_{g}")
D = pd.get_dummies(p[["unit", "month"]], drop_first=True, dtype=float)
Xmat = sm.add_constant(pd.concat([p[cols].reset_index(drop=True), D.reset_index(drop=True)], axis=1))
y = p.y.reset_index(drop=True)

print(f"관측 {len(p):,} | 계약 단위 {p.unit.nunique()} | 가격공식 군집 {p.fcl.nunique()} | 월 {p.month.nunique()}")
print(p.groupby("g").agg(계약단위=("unit", "nunique"), 공식군집=("fcl", "nunique"), 관측=("y", "size")))

res_unit = sm.OLS(y, Xmat).fit(cov_type="cluster", cov_kwds={"groups": p.unit.factorize()[0]})
res_fcl = sm.OLS(y, Xmat).fit(cov_type="cluster", cov_kwds={"groups": p.fcl.factorize()[0]})

def cumulative(r, g):
    n = [f"{g}_{L}" for L in range(4)]
    return r.params[n].sum(), np.sqrt(r.cov_params().loc[n, n].values.sum())

# %%
# 와일드 클러스터 부트스트랩 (귀무가설 Σβ = 0 을 제약해서 재표본) — 1~2분 걸립니다
rng = np.random.default_rng(20261012)
cl = p.fcl.factorize()[0]; G = cl.max() + 1
W6 = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
Xv = Xmat.values
XtX_inv = np.linalg.pinv(Xv.T @ Xv)
masks = [cl == c for c in range(G)]

def cluster_se_of_sum(e, idx):
    meat = np.zeros((Xv.shape[1], Xv.shape[1]))
    for m in masks:
        s = Xv[m].T @ e[m]; meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    w = np.zeros(Xv.shape[1]); w[idx] = 1
    return np.sqrt(w @ V @ w)

def wild_cluster_bootstrap(g, B=999):
    names = [f"{g}_{L}" for L in range(4)]
    idx = [Xmat.columns.get_loc(n) for n in names]
    beta = XtX_inv @ Xv.T @ y.values; e = y.values - Xv @ beta
    t0 = beta[idx].sum() / cluster_se_of_sum(e, idx)
    Xr = Xmat.copy()                                   # 제약 모형: β3 = −(β0+β1+β2)
    for L in range(3): Xr[names[L]] = Xmat[names[L]] - Xmat[names[3]]
    Xr = Xr.drop(columns=[names[3]])
    br = np.linalg.lstsq(Xr.values, y.values, rcond=None)[0]
    yhat_r = Xr.values @ br; er = y.values - yhat_r
    ts = np.empty(B)
    for i in range(B):
        ys = yhat_r + rng.choice(W6, G)[cl] * er
        bs = XtX_inv @ Xv.T @ ys
        ts[i] = bs[idx].sum() / cluster_se_of_sum(ys - Xv @ bs, idx)
    return (np.abs(ts) >= abs(t0)).mean()

rows = []
for g in GS:
    v, se_u = cumulative(res_unit, g); _, se_f = cumulative(res_fcl, g)
    rows.append(dict(유형=GNAME[g], 고정가_대비_차이=round(v, 3), se_계약군집=round(se_u, 3),
                     se_공식군집=round(se_f, 3), p_와일드부트스트랩=round(wild_cluster_bootstrap(g), 3),
                     처치군_공식수=p[p.g == g].fcl.nunique()))
FE = pd.DataFrame(rows)
FE.to_csv(OUT / "panel_fe_results.csv", index=False)
print("== 유가 1% 변화 → 단가 %p 차이 (고정가 대비, 0~3개월 누적) ==")
print(FE.to_string(index=False))

# %% [markdown]
# **읽는 법**: 빠른 연동 재생 계약은 유가가 1% 오르면 고정가 계약보다 단가가 약 0.56% 더 오릅니다(3개월 안).
# 느린 연동(Pakini Nui)은 월 단위로는 거의 반응하지 않습니다. 이 계약은 유가의 3~4년 평균을 따라가기 때문입니다.
#
# **강건성 점검(추가)**: 빠른 연동 재생의 "처치 군집"은 3개뿐입니다. 군집이 이렇게 적으면
# 와일드 부트스트랩 p값도 정확도가 떨어질 수 있습니다.
# 그래서 가격 공식 하나씩 따로 추정해, 결과가 한 공식에 끌려가는지 봅니다.

# %%
treated = p[p.g.isin(["REN", "FOS"])].fcl.unique()
p2 = p.copy(); cols2 = []
for f in treated:
    for L in range(4):
        c = f"F{list(treated).index(f)}_{L}"
        p2[c] = p2[f"d{L}"] * (p2.fcl == f); cols2.append(c)
for L in range(4):
    p2[f"LAG_{L}"] = p2[f"d{L}"] * (p2.g == "LAG"); cols2.append(f"LAG_{L}")
cols2 += [c for c in cols if c.startswith("jan_")]
X2 = sm.add_constant(pd.concat([p2[cols2].reset_index(drop=True), D.reset_index(drop=True)], axis=1))
r2 = sm.OLS(y, X2).fit()   # 점추정만 봅니다 (공식 하나 안에서는 군집 표준오차를 낼 수 없음)
rows = []
for k, f in enumerate(treated):
    n = [f"F{k}_{L}" for L in range(4)]
    sub = p2[p2.fcl == f]
    rows.append(dict(가격공식=f, 유형=GNAME[sub.g.iloc[0]], 계약수=sub.unit.nunique(), 관측=len(sub),
                     고정가_대비_차이=round(r2.params[n].sum(), 3)))
BYF = pd.DataFrame(rows).sort_values(["유형", "고정가_대비_차이"])
BYF.to_csv(OUT / "panel_by_formula.csv", index=False)
print(BYF.to_string(index=False))
print(f"\n빠른 연동 재생 공식별 추정치 범위: {BYF[BYF.유형 == '빠른 연동(재생)'].고정가_대비_차이.min():.2f} ~ {BYF[BYF.유형 == '빠른 연동(재생)'].고정가_대비_차이.max():.2f}")

# %% [markdown]
# ## 4. 메인 ② 보험 평가: 보험료·보험금, 공정 고정가, 최악·최선 5%
#
# **월 효과**(하와이섬 요금 ¢/kWh) = (유가 연동 단가 − 고정가) × 계약 구매비중 × 구매전력 비중 × 1.062 × 1.0975
#
# - 유가 연동 단가 = 전환 전에는 그 계약의 실제 단가, 전환 후에는 같은 달 PGV 단가(전환 전엔 둘이 같았음)
# - **양수 = 고정가 덕에 아낀 돈(보험금)**, **음수 = 고정가라서 더 낸 돈(보험료)**
# - A = 전환 후 실제, B = "2015년부터 고정가였다면"(가상)

# %%
hh = panel[(panel.island == "hawaii") & (panel.price_cents_kwh > 0)]
pgv = hh[hh.contract == "PGV"].groupby("month").price_cents_kwh.mean()
rows = []
for con, sw in SWITCH.items():
    d = hh[hh.contract == con].groupby("month").agg(price=("price_cents_kwh", "mean"),
                                                    share=("share_of_purchased_pct", "sum"))
    fixed = d.loc[d.index >= sw, "price"].median()
    for m, r in d.iterrows():
        post = m >= sw
        if m < "2015-01" or m not in hi.index or (post and m not in pgv.index):
            continue
        S = pgv[m] if post else r.price
        w = r.share / 100 * hi.loc[m, "purchased_share_of_system_pct"] / 100 * LF * RT
        rows.append(dict(month=m, contract=con, fixed_price=fixed, indexed_price=S, actual_price=r.price,
                         post=post, weight=w, effect_cents=(S - fixed) * w, period=shock_label(m)))
HM = pd.DataFrame(rows)
HM.to_csv(OUT / "hedge_monthly.csv", index=False)
print("고정가:", HM.groupby("contract").fixed_price.first().to_dict())

def summarize(d, label):
    g = d.groupby("month").effect_cents.sum().to_frame("e"); g["period"] = g.index.map(shock_label)
    out = [dict(scenario=label, period=per, months=len(x), avg_cents_kwh=round(x.e.mean(), 3),
                hh500_per_month=round(x.e.mean() * 5, 2), hh500_total=round(x.e.sum() * 5, 1))
           for per, x in g.groupby("period")]
    out.append(dict(scenario=label, period="전체", months=len(g), avg_cents_kwh=round(g.e.mean(), 3),
                    hh500_per_month=round(g.e.mean() * 5, 2), hh500_total=round(g.e.sum() * 5, 1)))
    return out
HS = pd.DataFrame(summarize(HM[HM.post], "A 실제(전환 후), 두 계약 합")
                  + summarize(HM[HM.contract == "Hawi Renewable Dev."], "B 가상(2015부터 고정), Hawi")
                  + summarize(HM[HM.contract == "Wailuku Hydro"], "B 가상(2015부터 고정), Wailuku"))
HS.to_csv(OUT / "hedge_summary.csv", index=False)
print("\n== 보험금(+)/보험료(−): 하와이섬 요금 ¢/kWh, 500kWh 가구 $ ==")
print(HS.to_string(index=False))

# %%
# 12개월 손익 분포 (역사적 시뮬레이션), 공정 고정가 K*
hw = HM[HM.contract == "Hawi Renewable Dev."].set_index("month").sort_index()
hw["pi"] = hw.indexed_price - hw.fixed_price            # 구매자 손익 ¢/kWh (+ 고정가가 이득)
hw["hh"] = hw.effect_cents * 5                          # 500kWh 가구 월 $

def tail(x, q=0.05):
    x = np.asarray(pd.Series(x).dropna()); lo, hi_ = np.quantile(x, q), np.quantile(x, 1 - q)
    return dict(mean=x.mean(), sd=x.std(ddof=1), VaR5=lo, ES5=x[x <= lo].mean(),
                VaR95=hi_, ES95=x[x >= hi_].mean(), share_neg=(x < 0).mean(), n=len(x))
r_pi, r_hh = hw.pi.rolling(12).mean(), hw.hh.rolling(12).sum()
HR = pd.DataFrame([dict(metric="계약 단가: 12개월 평균 (연동 − 고정) ¢/kWh", **tail(r_pi)),
                   dict(metric="500kWh 가구: 12개월 합계 $", **tail(r_hh))])
HR.to_csv(OUT / "hedge_risk.csv", index=False)
print(HR.round(3).to_string(index=False))

def fair_price(d, rate=0.0, a=None, z=None):
    d = d.loc[a:z]
    disc = (1 + rate) ** (-np.arange(len(d)) / 12)
    return (d.weight * d.indexed_price * disc).sum() / (d.weight * disc).sum()

print("\n== 공정 고정가 K* (기대 손익이 0이 되는 고정가, 구매량 가중) ==")
KS = []
for con in SWITCH:
    d = HM[HM.contract == con].set_index("month").sort_index()
    K = d.fixed_price.iloc[0]
    for lab, a, z, rate in [("2015~2026", None, None, 0.0), ("2015~2026, 할인 5%", None, None, 0.05),
                            ("2015~2019", "2015-01", "2019-12", 0.0), ("2019~2026", "2019-01", "2026-10", 0.0),
                            ("2021~2026", "2021-01", "2026-10", 0.0)]:
        KS.append(dict(계약=con, 실제_고정가=K, 구간=lab, 공정_고정가=round(fair_price(d, rate, a, z), 2)))
KS = pd.DataFrame(KS); KS.to_csv(OUT / "fair_price.csv", index=False)
print(KS.to_string(index=False))

# %% [markdown]
# **보험의 두 얼굴 분해 (추가 분석)**
#
# 고정가 계약의 누적 손익은 수학적으로 두 부분으로 나뉩니다.
#
# $$\sum_t w_t(S_t - K) = \underbrace{\sum_t w_t (K^* - K)}_{\text{가격 수준: 싸게 계약했나}} + \underbrace{\sum_t w_t (S_t - K^*)}_{\text{타이밍: 정의상 합 0}}$$
#
# 공정 고정가 K*의 정의상 둘째 항은 전체 기간 합이 0입니다. 그러니 **"15년 동안 얼마를 아꼈나"는 전부 가격 수준(K* − K)에서 나옵니다.**
# 보험의 진짜 가치는 평균이 아니라 **변동성을 없앤 것**(충격 때 몰린 비용을 평평하게 만든 것)에 있습니다. 아래 표가 이를 보여줍니다.

# %%
rows = []
for con in SWITCH:
    d = HM[HM.contract == con].set_index("month").sort_index()
    K, Ks = d.fixed_price.iloc[0], fair_price(d)
    level = (d.weight * (Ks - K)).sum() * 5
    timing = (d.weight * (d.indexed_price - Ks)).sum() * 5
    eff_idx = d.weight * d.indexed_price * 5       # 연동이었다면 이 계약이 가구 요금에 더한 몫 (월 $)
    eff_fix = d.weight * K * 5                      # 고정가일 때
    rows.append({"계약": con, "고정가": K, "공정고정가": round(Ks, 2),
                 "누적손익_가구$": round(level + timing, 1), "그중_가격수준$": round(level, 1), "그중_타이밍$": round(timing, 1),
                 "연동시_월부담_sd$": round(eff_idx.std(), 2), "고정시_월부담_sd$": round(eff_fix.std(), 2)})
DEC = pd.DataFrame(rows); DEC.to_csv(OUT / "hedge_decomposition.csv", index=False)
print(DEC.to_string(index=False))
print("\n※ 고정 시에도 표준편차가 0이 아닌 이유: 구매 비중(물량)이 달마다 바뀌기 때문")
print("※ Wailuku의 '아낀 돈'은 전부 가격 수준(7¢ ≪ 공정가 16¢)에서 나옴 → 보험금이 아니라 '싸게 재계약한 효과'")

# %% [markdown]
# **사전 공정 고정가 (추가 분석, 연구 디벨롭용 시연)**
#
# 위의 K*는 "사후에 보니" 공정했는지입니다. 그런데 구간을 어디로 잡느냐에 따라 12¢~20¢로 크게 흔들립니다.
# 계약을 맺던 **그 시점에 알 수 있던 정보로** 공정했는지를 보려면, 당시의 유가 기대치를 연동 공식에 넣어야 합니다(예: 계약 당시의 선물가격).
#
# 여기서는 가장 단순한 기대치인 **"유가가 계약 당시 수준 그대로"(랜덤워크)**로 시연합니다.
# 실제 연구에서는 `EXPECTED_BRENT`에 EIA 단기전망(STEO) 또는 선물가격 경로를 넣으면 됩니다.

# %%
# 1) 연동 단가 공식 추정: ln(PGV 단가) = a + b·ln(브렌트, 2개월 시차)  — 계약 당시까지의 자료만 사용
def exante_fair(sign_month, horizon_years=10, expected=None):
    d = pd.DataFrame({"lp": np.log(pgv), "lb": np.log(brent).shift(2).reindex(pgv.index)}).dropna().loc[:sign_month]
    fit = sm.OLS(d.lp, sm.add_constant(d.lb)).fit()
    smear = np.mean(np.exp(fit.resid))                          # 로그 → 원 단위 보정
    b0 = brent.loc[:sign_month].iloc[-1]                        # 계약 당시 알던 최신 유가
    path = np.full(12 * horizon_years, b0) if expected is None else np.asarray(expected, float)
    S_hat = np.exp(fit.params.const + fit.params.lb * np.log(path)) * smear
    return dict(계약시점=sign_month, 당시_브렌트=round(b0, 1), 탄력성_b=round(fit.params.lb, 2),
                사전_공정고정가=round(S_hat.mean(), 2))
EXPECTED_BRENT = None      # 예: EIA STEO 2023년 5월호의 월별 브렌트 전망을 리스트로 넣기
EA = pd.DataFrame([dict(계약="Hawi Renewable Dev.", 실제_고정가=15.5, **exante_fair("2023-04", expected=EXPECTED_BRENT)),
                   dict(계약="Wailuku Hydro", 실제_고정가=7.0, **exante_fair("2025-03", expected=EXPECTED_BRENT))])
EA.to_csv(OUT / "fair_price_exante.csv", index=False)
print(EA.to_string(index=False))
print("\n※ 계약 시점은 보도자료 날짜(Hawi 2023.5.22, Wailuku 2025.4) 직전 달로 둠. 랜덤워크 가정이라 시연용입니다.")

# %%
# 구매자 입장: 계약 방식별 12개월 평균 단가 분포
Sx = pd.DataFrame({"고정가 (15.5¢)": 15.5, "빠른 연동 (PGV)": hw.indexed_price,
                   "느린 연동 (Pakini Nui)": pv["Tawhiri (Pakini Nui)"].reindex(hw.index)})
rows = []
for c in Sx:
    rr = Sx[c].rolling(12).mean(); t = tail(rr)
    rows.append(dict(type=c, mean=t["mean"], sd=t["sd"], best5=t["VaR5"], worst5=t["VaR95"],
                     worst_ES=t["ES95"], max_12m_jump=rr.diff(12).max()))
CR = pd.DataFrame(rows); CR.to_csv(OUT / "contract_cost_risk.csv", index=False)
print("== 구매자 입장: 12개월 평균 단가 분포 (¢/kWh) ==")
print(CR.round(2).to_string(index=False))

# %%
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), gridspec_kw=dict(width_ratios=[1.5, 1, 1]))
v = hw.hh
c = [("#c05621" if val > 0 else "#2d3748") if post else ("#f6ad55" if val > 0 else "#a0aec0")
     for val, post in zip(v.values, hw.post.values)]
ax[0].bar(pd.to_datetime(v.index), v.values, width=25, color=c)
for r in shocks.itertuples():
    ax[0].axvspan(pd.to_datetime(r.start), pd.to_datetime(r.end) + pd.offsets.MonthEnd(0),
                  color=COL["up"] if r.type == "급등" else COL["down"], alpha=0.10, lw=0)
ax[0].axvline(pd.to_datetime("2023-09"), color="k", ls="--", lw=1)
ax[0].text(pd.to_datetime("2023-10"), v.min() * 0.9, "실제 전환", fontsize=9)
ax[0].axhline(0, color="k", lw=0.8)
ax[0].set_ylabel("500kWh 가구 월 $ (+ 아낌, − 더 냄)")
ax[0].set_title("① Hawi 15.5¢: 월별 보험금·보험료\n(옅은 색 = 전환 전 가상, 진한 색 = 전환 후 실제)", loc="left", fontsize=10)
xx = r_hh.dropna(); t = tail(r_hh)
ax[1].hist(xx, bins=25, color="#a0aec0", edgecolor="w")
for val, lab, col in [(t["VaR5"], "최악 5%", "#2d3748"), (t["mean"], "평균", COL["fix"]), (t["VaR95"], "최선 5%", "#c05621")]:
    ax[1].axvline(val, color=col, lw=2); ax[1].text(val, ax[1].get_ylim()[1] * 0.92, f" {lab}\n {val:+.1f}$", color=col, fontsize=8.5)
ax[1].set_xlabel("12개월 합계 $"); ax[1].set_title("② 1년 손익 분포", loc="left", fontsize=10)
for k, col in zip(Sx, [COL["fix"], COL["fast"], COL["slow"]]):
    ax[2].plot(pd.to_datetime(Sx.index), Sx[k].rolling(12).mean(), color=col, lw=2, label=k)
ax[2].set_ylabel("12개월 평균 단가 (¢/kWh)"); ax[2].legend(fontsize=8)
ax[2].set_title("③ 구매자 입장 계약 방식별 단가", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig3_hedge.png", dpi=150); plt.show()

# %% [markdown]
# ## 5. 유가 연동 계약이 하와이섬 요금에 더한 몫 (2019~2026)
#
# 기준: 각 계약 단가가 평상시(2019.2~2021.12) 평균에 묶여 있었다면.
# 효과 = Σ(단가 − 평상시 단가) × 구매비중 × 구매전력 비중 × 1.062 × 1.0975.
# 2019년 이전은 요금 계산 방식(ECAC)이 달라 이 분석은 2019년부터만 합니다.

# %%
r = panel[(panel.island == "hawaii") & (panel.category == "renewable") & (panel.price_cents_kwh > 0)].copy()
r["ftype"] = r.formula.map({"OIL_INDEXED": "빠른 연동", "LAGGED_INDEXED": "느린 연동"}).fillna("고정")
base = r[r.month.between("2019-02", "2021-12")].groupby("source").price_cents_kwh.mean()
r["base"] = r.source.map(base); r = r[r.base.notna() & (r.month >= "2019-02")]
r["eff"] = (r.price_cents_kwh - r.base) * r.share_of_purchased_pct / 100
FM = r.groupby(["month", "ftype"]).eff.sum().unstack(fill_value=0)
FM = FM.mul(hi.loc[FM.index, "purchased_share_of_system_pct"] / 100 * LF * RT, axis=0)
FM.to_csv(OUT / "hawaii_formula_effects_monthly.csv")
lab = pd.Series([shock_label(m) for m in FM.index], index=FM.index)
EV = FM.assign(합계=FM[["빠른 연동", "느린 연동"]].sum(axis=1)).groupby(lab)[["빠른 연동", "느린 연동", "합계"]].mean().round(2)
EV["500kWh가구_월$"] = (EV["합계"] * 5).round(1); EV["months"] = lab.value_counts()
EV.to_csv(OUT / "hawaii_event_effects.csv")
print("== 충격 구간별: 유가 연동 계약이 하와이섬 요금에 더한 몫 (¢/kWh, 평상시 단가 대비) ==")
print(EV)

# %% [markdown]
# ## 6. 보조 분석
# ### 6-1. 같은 발전소(PGV) 안 계약 비교
# PGV 지열 발전소에는 계약이 3개 있습니다. 기본분은 유가 연동이고, 추가 5MW·8MW는 고정가(+1월 인상)입니다.
# 발전소·연료·운영자가 같은데 가격 방식만 다릅니다.

# %%
g = hh[hh.contract.str.startswith("PGV")].groupby(["contract", "month"]).price_cents_kwh.mean().reset_index()
rows = []
for con, d in g.groupby("contract"):
    d = d.set_index("month").sort_index()
    df = pd.DataFrame({"y": np.log(d.price_cents_kwh).diff()}).join(pd.DataFrame({f"l{k}": db.shift(k) for k in range(4)})).dropna()
    ok = (pd.to_datetime(pd.Series(d.index)).diff().dt.days <= 31).values
    df = df[df.index.isin(d.index[ok])]
    df["jan"] = df.index.str.endswith("-01").astype(int)
    res = sm.OLS(df.y, sm.add_constant(df[[f"l{k}" for k in range(4)] + ["jan"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    n = [f"l{k}" for k in range(4)]
    rows.append(dict(contract=con, formula=panel[(panel.island == "hawaii") & (panel.contract == con)].formula.iloc[0],
                     months=len(df), passthrough=round(res.params[n].sum(), 3),
                     se=round(np.sqrt(res.cov_params().loc[n, n].values.sum()), 3)))
PG = pd.DataFrame(rows); PG.to_csv(OUT / "pgv_tranches.csv", index=False)
print("== PGV 발전소 안: 유가 1% → 단가 % (0~3개월 누적, 2015~2026) ==")
print(PG.to_string(index=False))

# %% [markdown]
# ### 6-2. 고정가 전환 이벤트 스터디와 위약 검정
# 결과 = ln(전환 계약 단가) − ln(PGV 단가), x = ln 브렌트(2개월 시차).
# 전환 시점 기준 12개월 구간마다 "유가 반응 차이" δ를 추정합니다(기준 구간: 전환 직전 12개월).

# %%
pe = panel[panel.price_cents_kwh > 0]
pe = pe[pe.price_cents_kwh >= 0.5 * pe.groupby(["island", "source", "regime"]).price_cents_kwh.transform("median")]
PL = pe.groupby(["island", "contract", "month"]).price_cents_kwh.mean().reset_index()
xs = np.log(brent).shift(2)
def lnp(isl_, con):
    return np.log(PL[(PL.island == isl_) & (PL.contract == con)].set_index("month").price_cents_kwh.sort_index())
ctrl = lnp("hawaii", "PGV")
BINS, REF = list(range(-60, 36, 12)), -12
def rel(m, sw): return (pd.Period(m, "M") - pd.Period(sw, "M")).n

def cohort_est(yt, sw):
    d = pd.DataFrame({"y": yt - ctrl.reindex(yt.index), "x": xs.reindex(yt.index)}).dropna()
    d["k"] = [(rel(m, sw) // 12) * 12 for m in d.index]; d = d[d.k.isin(BINS)]
    ks = [k for k in sorted(d.k.unique()) if k != REF]
    Z = pd.DataFrame({f"k{k}": (d.k == k) * d.x for k in ks}, index=d.index)
    for k in sorted(d.k.unique()): Z[f"c{k}"] = (d.k == k).astype(float)
    res = sm.OLS(d.y, Z).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    out = pd.DataFrame({"k": ks, "delta": [res.params[f"k{k}"] for k in ks], "se": [res.bse[f"k{k}"] for k in ks],
                        "n": [int((d.k == k).sum()) for k in ks]})
    return pd.concat([out, pd.DataFrame({"k": [REF], "delta": [0.0], "se": [0.0], "n": [int((d.k == REF).sum())]})]).sort_values("k")

C = pd.concat([cohort_est(lnp("hawaii", con), sw).assign(cohort=con) for con, sw in SWITCH.items()])
def iw(g):
    w = g.n / g.n.sum()
    return pd.Series({"delta": (w * g.delta).sum(), "se": np.sqrt((w ** 2 * g.se ** 2).sum()), "cohorts": len(g), "n": g.n.sum()})
IW = C[C.n > 0].groupby("k").apply(iw).reset_index()
IW.to_csv(OUT / "event_study.csv", index=False); C.to_csv(OUT / "event_study_cohort.csv", index=False)
print(IW.round(3).to_string(index=False))

def did_slope(yt, sw):
    d = pd.DataFrame({"y": yt - ctrl.reindex(yt.index), "x": xs.reindex(yt.index)}).dropna()
    d["r"] = [rel(m, sw) for m in d.index]
    if (d.r >= 0).sum() < 6 or (d.r < 0).sum() < 6: return np.nan
    Z = sm.add_constant(pd.DataFrame({"x": d.x, "xpost": d.x * (d.r >= 0), "post": (d.r >= 0).astype(float)}))
    return sm.OLS(d.y, Z).fit().params["xpost"]

actual = {con: did_slope(lnp("hawaii", con), sw) for con, sw in SWITCH.items()}
print("\n실제 효과 (전환 후 유가 반응 변화):", {k: round(v, 3) for k, v in actual.items()})
hawi_pre = lnp("hawaii", "Hawi Renewable Dev.").loc[:"2023-08"]
pa = pd.DataFrame({"placebo": "가짜 시점(Hawi)", "unit": [str(m) for m in pd.period_range("2017-01", "2021-08", freq="M")]})
pa["effect"] = [did_slope(hawi_pre, m) for m in pa.unit]
units = PL.groupby(["island", "contract"]).month.count().reset_index()
units = units[(units.month >= 60) & ~units.contract.isin(list(SWITCH) + ["PGV"])]
pb = pd.DataFrame([dict(placebo=f"가짜 계약({sw})", unit=f"{u.island}|{u.contract}", effect=did_slope(lnp(u.island, u.contract), sw))
                   for u in units.itertuples() for con, sw in SWITCH.items()]).dropna()
PLA = pd.concat([pa, pb]).dropna(); PLA.to_csv(OUT / "event_placebo.csv", index=False)
for nm, g_ in PLA.groupby("placebo"):
    a = actual["Hawi Renewable Dev."] if ("Hawi" in nm or "2023" in nm) else actual["Wailuku Hydro"]
    pval = (1 + (g_.effect.abs() >= abs(a)).sum()) / (len(g_) + 1)
    print(f"{nm}: {len(g_)}개, 가짜 효과 범위 [{g_.effect.min():.3f}, {g_.effect.max():.3f}], 무작위화 p = {pval:.3f}")

# %% [markdown]
# **주의해서 읽기**: 전환 전 구간의 δ가 0.000으로 나오는 것은 "평행 추세가 검증됐다"는 뜻이 아니라,
# 전환 전엔 두 계약이 **같은 단가표라 단가가 똑같았기 때문에 생기는 항등식**입니다. 가짜 시점 위약도 같은 이유로 자동 통과합니다.
# 전환 후 δ ≈ −0.5~−0.9도 "고정가는 유가에 안 움직인다"는 계약 정의를 다시 확인한 것입니다.
# 그래서 이 분석은 **"공시 단가가 보도자료의 전환 조건대로 움직였다"는 검증**으로 쓰는 것이 정확합니다.

# %%
fig, ax = plt.subplots(1, 2, figsize=(13, 4.3), gridspec_kw=dict(width_ratios=[1.5, 1]))
ax[0].axhline(0, color="k", lw=.8); ax[0].axvline(0, color="#c53030", ls="--", lw=1)
ax[0].errorbar(IW.k + 5.5, IW.delta, yerr=1.96 * IW.se, fmt="o", color=COL["fix"], capsize=3)
ax[0].set_xlabel("고정가 전환 기준 개월 (12개월 구간)"); ax[0].set_ylabel("유가 반응 차이 (전환 계약 − PGV)")
ax[0].set_title("① 이벤트 스터디: 전환 후 유가 반응 소멸", loc="left", fontsize=10)
for nm, g_ in PLA.groupby("placebo"):
    ax[1].hist(g_.effect.clip(-0.79, 0.59), bins=np.linspace(-0.8, 0.6, 29), alpha=.55, label=f"{nm} ({len(g_)}개)")
for v_ in actual.values(): ax[1].axvline(v_, color="#c53030", lw=2)
ax[1].set_title("② 위약 분포와 실제 효과(빨강)", loc="left", fontsize=10); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "fig4_event_study.png", dpi=150); plt.show()

# %% [markdown]
# ## 7. 저장된 결과표(04_results)와 대조
# 이 노트북이 같은 숫자를 내는지 확인합니다. 차이가 0에 가까우면 재현 성공입니다.

# %%
R = DATA / "04_results"
def cmp(name, new, key, cols_new, cols_old=None, old=None):
    old = pd.read_csv(R / name) if old is None else old
    cols_old = cols_old or cols_new
    m = new.merge(old, on=key, suffixes=("_new", "_old"))
    diffs = [(m[f"{a}_new"] - m[f"{b_}_old"]).abs().max() if a == b_ else (m[a] - m[b_]).abs().max()
             for a, b_ in zip(cols_new, cols_old)]
    return dict(결과표=name, 비교행=len(m), 최대차이=float(np.nanmax(diffs)))
old_fe = pd.read_csv(R / "panel_fe_results.csv")
old_hs = pd.read_csv(R / "hedge_summary.csv"); old_hs["scenario"] = old_hs.scenario.str.replace("2019부터", "2015부터")
checks = [
    cmp("shock_windows.csv", shocks, ["start", "end"], ["months", "peak_dev"]),
    cmp("panel_fe_results.csv", FE, ["유형"], ["고정가_대비_차이", "se_공식군집", "p_와일드부트스트랩"],
        old=old_fe.assign(유형=old_fe.유형.str.replace("유가 연동(재생)", "빠른 연동(재생)", regex=False))),
    cmp("hedge_summary.csv", HS, ["scenario", "period"], ["hh500_total"], old=old_hs),
    cmp("hedge_risk.csv", HR, ["metric"], ["mean", "VaR5", "VaR95"]),
    cmp("pgv_tranches.csv", PG, ["contract"], ["passthrough"]),
    cmp("event_study.csv", IW, ["k"], ["delta"]),
]
print(pd.DataFrame(checks).to_string(index=False))

# %% [markdown]
# ## 결과 요약 (자동 생성)

# %%
hs = HS.set_index(["scenario", "period"])
dec = DEC.set_index("계약")
print(f"""
[충격] 1990~2014 기준(T={T_MAIN})으로 {len(shocks)}개 충격 탐지: {', '.join(shock_label(r.start) for r in shocks.itertuples())}

[메인 ①] 고정가 대비 유가 1% 변화 시 단가 반응 차이 (3개월 누적)
  빠른 연동 재생 {FE.iloc[0].고정가_대비_차이:+.2f}  (공식군집 se {FE.iloc[0].se_공식군집:.2f}, WCB p={FE.iloc[0].p_와일드부트스트랩:.3f}, 처치 공식 {FE.iloc[0].처치군_공식수}개)
  유가 연동 화석 {FE.iloc[1].고정가_대비_차이:+.2f}  (WCB p={FE.iloc[1].p_와일드부트스트랩:.3f})
  느린 연동     {FE.iloc[2].고정가_대비_차이:+.2f}  (WCB p={FE.iloc[2].p_와일드부트스트랩:.3f})

[메인 ②] Hawi 15.5¢ (2015~2026, 500kWh 가구)
  공정 고정가 K* = {dec.loc['Hawi Renewable Dev.', '공정고정가']}¢ → 누적 {dec.loc['Hawi Renewable Dev.', '누적손익_가구$']:+.1f}$ (거의 공정)
  1년 손익: 평균 {HR.iloc[1]['mean']:+.1f}$, 최악 5% {HR.iloc[1].VaR5:+.1f}$, 최선 5% {HR.iloc[1].VaR95:+.1f}$
  2021~22 급등 보험금 {hs.loc[('B 가상(2015부터 고정), Hawi', '2021~22 급등'), 'hh500_total']:+.1f}$, 2015~16 폭락 보험료 {hs.loc[('B 가상(2015부터 고정), Hawi', '2015~16 폭락'), 'hh500_total']:+.1f}$
  Wailuku 7¢: 공정 고정가 {dec.loc['Wailuku Hydro', '공정고정가']}¢ → 누적 {dec.loc['Wailuku Hydro', '누적손익_가구$']:+.1f}$ 중 가격 수준 몫 {dec.loc['Wailuku Hydro', '그중_가격수준$']:+.1f}$
  실제(전환 후) 두 계약 합: {hs.loc[('A 실제(전환 후), 두 계약 합', '전체'), 'hh500_total']:+.1f}$ ({hs.loc[('A 실제(전환 후), 두 계약 합', '전체'), 'months']}개월)
""")
