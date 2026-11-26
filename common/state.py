"""
state.py — 앱 전체에서 쓰는 st.session_state 키 규칙

규칙
1. 키 이름은 이 파일의 상수로만 쓴다. 페이지에서 문자열을 직접 쓰지 않는다.
2. 값을 바꾸는 곳(setter)은 아래 표의 '설정하는 곳' 한 군데뿐이다. 나머지 페이지는 읽기만 한다.
3. 위젯 key에는 상태 키와 다른 이름(_w_ 접두사)을 쓰고 on_change로 상태 키에 복사한다.
4. 키를 추가하거나 바꿀 때는 README의 키 표를 먼저 수정한다.
"""
import copy
import streamlit as st

# ── 키 이름 ────────────────────────────────────────────
YEAR = "year"                  # int          기준 연도
MIN_STORES = "min_stores"      # int          최소 가맹점수(전년도). 5 / 10 / 20
SECTOR = "sector"              # str | None   업종 중분류. None = 전체
BUDGET_RANGE = "budget_range"  # (int, int)   창업비용 범위, 단위 천원
REGION = "region"              # str | None   비교 지역(시도). 참고용
WEIGHTS = "weights"            # dict         closure/growth/sales/multiple
CANDIDATES = "candidates"      # list[str]    후보 브랜드 brand_id
COMPARE_SET = "compare_set"    # list[str]    비교 대상 brand_id (최대 4개)
HIDE_NEW = "hide_new"          # bool         신규 브랜드 제외 토글. 기본 True

# ── 기본값 ─────────────────────────────────────────────
DEFAULTS = {
    YEAR: 2025,
    MIN_STORES: 10,
    SECTOR: None,
    BUDGET_RANGE: (0, 500_000),
    REGION: None,
    WEIGHTS: {"closure": 0.30, "growth": 0.20, "sales": 0.20, "multiple": 0.30},
    CANDIDATES: [],
    COMPARE_SET: [],
    HIDE_NEW: True,
}

MAX_COMPARE = 4


def init_state():
    """모든 페이지 맨 위에서 호출. 아직 없는 키만 기본값으로 채운다."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


def make_brand_id(corp_nm, brand_nm, mlsfc_nm):
    """브랜드 식별자. 연도는 넣지 않는다(브랜드는 연도에 걸쳐 같은 대상)."""
    return f"{corp_nm}|{brand_nm}|{mlsfc_nm}"


def add_compare(brand_id):
    """비교 대상에 추가. 최대 MAX_COMPARE개. 추가되면 True."""
    items = st.session_state[COMPARE_SET]
    if brand_id in items or len(items) >= MAX_COMPARE:
        return False
    items.append(brand_id)
    return True