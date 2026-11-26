import pandas as pd
import streamlit as st
from metrics import compute_score


@st.cache_data
def get_scores(year, min_stores, weight_items=None):
    """weight_items: tuple(sorted(weights.items())). None이면 기본 가중치."""
    weights = dict(weight_items) if weight_items else None
    return compute_score(load_data(), year=year, min_stores=min_stores, weights=weights)


@st.cache_data
def get_scores(year, min_stores, weight_items=None):
    """weight_items: tuple(sorted(weights.items())). None이면 기본 가중치."""
    weights = dict(weight_items) if weight_items else None
    return compute_score(load_data(), year=year, min_stores=min_stores, weights=weights)

def _read(name):
    return pd.read_parquet(f"data/{name}.parquet")


@st.cache_data
def load_sector_trend():
    """업종 대분류별 신규 등록률·등록취소율 추이 (27행)"""
    return _read("sector_trend")


@st.cache_data
def load_sector_retention():
    """업종별·연차별 등록 유지율, 2021년 등록 브랜드 기준 (45행)"""
    return _read("sector_retention")


@st.cache_data
def load_region_sales():
    """시도별 업종 면적당 매출, 2022~2025 (2,992행)"""
    return _read("region_sales")


@st.cache_data
def load_sector_treemap():
    """업종 대분류→중분류별 브랜드 수·가맹점 수 (394행)"""
    return _read("sector_treemap")

SIDO_LIST = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
             "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]


def get_region_baseline(year, mid_sector, area):
    """해당 연도·업종(중분류)·시도의 평균 면적당 매출. 자료가 없으면 None.
    (region_sales는 2022년 이후만 있음. 단위는 브랜드의 arUnitAvrgSlsAmt와 같은 크기로 보임)"""
    d = load_region_sales()
    r = d[(d["yr"] == year) & (d["mid_sector"] == mid_sector) & (d["area"] == area)]["sales_per_area"].dropna()
    return float(r.iloc[0]) if len(r) else None