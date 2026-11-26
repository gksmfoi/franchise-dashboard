import streamlit as st
from common.state import YEAR, MIN_STORES, REGION
from common.data import SIDO_LIST

MIN_OPTIONS = [5, 10, 20]
MIN_YEAR = 2019
NO_REGION = "선택 안 함"


def _sync_year():
    st.session_state[YEAR] = st.session_state["_w_year"]


def _sync_min():
    st.session_state[MIN_STORES] = st.session_state["_w_min_stores"]


def render_sidebar(df):
    st.sidebar.header("필터")

    years = sorted((int(y) for y in df["yr"].unique() if y >= MIN_YEAR), reverse=True)
    st.sidebar.selectbox(
        "기준 연도",
        years,
        index=years.index(st.session_state[YEAR]),
        key="_w_year",
        on_change=_sync_year,
    )
    st.sidebar.selectbox(
        "최소 가맹점수(전년도)",
        MIN_OPTIONS,
        index=MIN_OPTIONS.index(st.session_state[MIN_STORES]),
        key="_w_min_stores",
        on_change=_sync_min,
    )



def _sync_region():
    v = st.session_state["_w_region"]
    st.session_state[REGION] = None if v == NO_REGION else v


def render_region_select(label="비교 지역"):
    """화면3 상단에 넣는 비교 지역 선택 상자. 고른 시도는 session_state[REGION]에 저장됨 (없으면 None)."""
    options = [NO_REGION] + SIDO_LIST
    cur = st.session_state[REGION]
    st.selectbox(label, options, index=options.index(cur) if cur in SIDO_LIST else 0,
                 key="_w_region", on_change=_sync_region)
    return st.session_state[REGION]