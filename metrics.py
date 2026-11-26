"""
metrics.py — 프랜차이즈 건전성 대시보드 지표 계산 모듈 (B 담당)
지표 정의서 기준

사용법:
    from metrics import build_metrics, compute_score
    bm = build_metrics("brand_frcs_stats.csv", "brand_fntn_stats.csv")
    result = compute_score(bm, year=2025, min_stores=10, weights=None)
"""
import html

import numpy as np
import pandas as pd

KEY = ["corpNm", "brandNm", "indutyMlsfcNm"]   # 같은 연도 안에서 브랜드를 구분하는 키 (+ yr)
BM = ["brandNm", "indutyMlsfcNm"]

METRICS = {  # 키: (컬럼, 높을수록 좋은가)
    "closure":  ("closure_rate",   False),
    "growth":   ("net_growth",     True),
    "sales":    ("avrgSlsAmt",     True),
    "multiple": ("sales_multiple", True),
}
DEFAULT_WEIGHTS = {"closure": .30, "growth": .20, "sales": .20, "multiple": .30}


def _clean_text(df):
    """HTML 기호 변환(&amp; → &), 앞뒤 공백 제거"""
    for c in ["corpNm", "brandNm", "indutyMlsfcNm", "indutyLclasNm"]:
        if c in df.columns:
            df[c] = df[c].astype(str).map(html.unescape).str.strip()
    return df


def _link_brands(frcs):
    """법인명만 바뀐 브랜드를 하나로 연결해 lineage(최초 법인 기준 키)를 붙임
    연결 조건: 같은 브랜드명·중분류에서 법인 A가 t-1년에 마지막으로 나오고 (가맹점 1개 이상 기준)
              다른 법인 B가 t년에 처음 나오며, 그 (브랜드명, 중분류, t)에 A·B가 각각 1개뿐일 때"""
    g = frcs.groupby(KEY)["yr"].agg(fy="min", ly="max").reset_index()
    old = g.rename(columns={"corpNm": "oldCorp"}).assign(t=lambda d: d["ly"] + 1)
    new = g.rename(columns={"corpNm": "newCorp"}).assign(t=lambda d: d["fy"])
    c = old[BM + ["oldCorp", "t"]].merge(new[BM + ["newCorp", "t"]], on=BM + ["t"])
    c = c[c["oldCorp"] != c["newCorp"]]
    c = c[c.groupby(BM + ["t"])["oldCorp"].transform("size") == 1]   # 1:1만 연결

    parent = {(r.newCorp, r.brandNm, r.indutyMlsfcNm): (r.oldCorp, r.brandNm, r.indutyMlsfcNm)
              for r in c.itertuples()}
    def root(k):
        while k in parent:
            k = parent[k]
        return k
    keys = list(zip(frcs["corpNm"], frcs["brandNm"], frcs["indutyMlsfcNm"]))
    frcs["lineage"] = ["|".join(root(k)) for k in keys]
    return frcs


def build_metrics(frcs_path, fntn_path):
    """원본 2개(가맹점 현황, 창업 금액) → brand_metrics 테이블"""
    frcs = _clean_text(pd.read_csv(frcs_path)).drop_duplicates(KEY + ["yr"])
    fntn = _clean_text(pd.read_csv(fntn_path)).drop_duplicates(KEY + ["yr"])

    # 분석 대상: 해당 연도 가맹점수 1개 이상 (0개 행은 폐업·이전 후 남은 기록)
    frcs = _link_brands(frcs[frcs["frcsCnt"] >= 1].copy())

    # 전년도 가맹점수 (법인명이 바뀌었어도 같은 브랜드면 이어서 계산)
    prev = frcs[["lineage", "yr", "frcsCnt"]].copy()
    prev["yr"] += 1
    prev = prev.rename(columns={"frcsCnt": "prevCnt"})

    df = frcs.merge(prev, on=["lineage", "yr"], how="left")
    df = df.merge(fntn[KEY + ["yr", "smtnAmt"]], on=KEY + ["yr"], how="left")

    # 0 = 미제공 → 결측
    for c in ["avrgSlsAmt", "arUnitAvrgSlsAmt", "smtnAmt"]:
        df[c] = df[c].replace(0, np.nan)

    # 지속성 지표 (명변경수 제외, 전년도 가맹점 0이거나 없으면 결측)
    df["closed"] = df["ctrtEndCnt"] + df["ctrtCncltnCnt"]
    has_prev = df["prevCnt"] > 0
    df["closure_rate"] = np.where(
        has_prev, df["closed"] / (df["prevCnt"] + df["newFrcsRgsCnt"]), np.nan)
    df["closure_rate"] = df["closure_rate"].clip(upper=1)            # 100% 상한
    df["net_growth"] = np.where(
        has_prev, (df["newFrcsRgsCnt"] - df["closed"]) / df["prevCnt"], np.nan)

    # 매출 지표
    df["sales_multiple"] = df["avrgSlsAmt"] / df["smtnAmt"]

    # 관측 연수 (해당 연도까지 누적) → 신규 브랜드
    df = df.sort_values(["lineage", "yr"])
    df["obs_years"] = df.groupby("lineage").cumcount() + 1
    df["is_new_brand"] = df["obs_years"] <= 2

    cols = ["yr", "indutyLclasNm", "indutyMlsfcNm", "corpNm", "brandNm",
            "frcsCnt", "prevCnt", "newFrcsRgsCnt", "ctrtEndCnt", "ctrtCncltnCnt", "closed",
            "closure_rate", "net_growth", "avrgSlsAmt", "arUnitAvrgSlsAmt", "smtnAmt",
            "sales_multiple", "obs_years", "is_new_brand"]
    return df[cols].reset_index(drop=True)


def compute_score(df, year=2025, min_stores=10, weights=None, min_group=10):
    """연도·최소 가맹점수·가중치 → 백분위 4개(pct_*) + 종합 점수(score)
    점수 산출 불가 브랜드는 score가 NaN"""
    w = dict(DEFAULT_WEIGHTS if weights is None else weights)
    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}                          # 합계 1로 정규화

    sub = df[(df["yr"] == year) & (df["prevCnt"] >= min_stores)].copy()
    cols = [c for c, _ in METRICS.values()]
    sub["scorable"] = sub[cols].notna().all(axis=1)

    # 중분류 산출 가능 브랜드가 min_group 미만이면 대분류 기준
    n_mid = sub[sub["scorable"]].groupby("indutyMlsfcNm").size()
    sub["rank_group"] = np.where(
        sub["indutyMlsfcNm"].map(n_mid).fillna(0) >= min_group,
        sub["indutyMlsfcNm"], sub["indutyLclasNm"])

    sc = sub[sub["scorable"]]
    for k, (col, higher_better) in METRICS.items():
        sub.loc[sc.index, f"pct_{k}"] = sc.groupby("rank_group")[col].rank(
            ascending=higher_better, pct=True, method="average")

    sub["score"] = sum(w[k] * sub[f"pct_{k}"] for k in METRICS) * 100
    return sub.sort_values("score", ascending=False, na_position="last")
