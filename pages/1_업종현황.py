import json

import pandas as pd
import streamlit as st

from common.state import init_state, SECTOR, YEAR
from common.data import load_data
from common.sidebar import render_sidebar
from common.footer import render_footer
from charts_sector import (render_sector_trend, render_sector_retention,
                           render_sector_treemap, render_region_map)

st.set_page_config(page_title="업종 현황", layout="wide")
init_state()
render_sidebar(load_data())

TM_KEY = "_w_treemap"          # 트리맵 위젯 key (위젯 key는 _w_ 로 시작 규칙)


# ── 데이터 불러오기 (한 번만 읽고 캐시) ────────────────────────
@st.cache_data
def load_tables():
    return {
        "trend":     pd.read_parquet("data/sector_trend.parquet"),
        "retention": pd.read_parquet("data/sector_retention.parquet"),
        "treemap":   pd.read_parquet("data/sector_treemap.parquet"),
        "region":    pd.read_parquet("data/region_sales.parquet"),
    }


@st.cache_data
def load_geo():
    with open("data/sido_geo.json", encoding="utf-8") as f:
        return json.load(f)


# ── 트리맵 클릭 → 상태(SECTOR) 저장 (화면1이 이 값을 바꾸는 유일한 곳) ──
def _pick_sector():
    pts = st.session_state[TM_KEY]["selection"]["points"]
    if pts and "/" in pts[0].get("id", ""):      # '대분류/중분류' 형태 = 중분류 칸
        st.session_state[SECTOR] = pts[0]["label"]


def _clear_sector():
    st.session_state[SECTOR] = None


T = load_tables()
year = st.session_state[YEAR]
sector = st.session_state[SECTOR]

st.title("업종 현황")
st.caption("업종별 추이와 유지율을 먼저 살펴본 뒤, 관심 있는 업종을 트리맵에서 클릭해 보세요. "
           "선택한 업종은 시도별 지도와 다음 화면(후보 탐색)에 이어집니다.")

# ── 1. 신규 등록률·등록취소율 (자료 보기) ────────────────────────
st.subheader("업종별 신규 등록률 · 등록취소율")
st.plotly_chart(render_sector_trend(T["trend"]), use_container_width=True)
st.caption(
    "업종 단위 등록취소율은 브랜드 폐점률과 산출 기준이 다릅니다.",
    help=("업종 등록취소율은 공정위 업종 통계의 값으로, 업종 전체 가맹점을 합산해 계산합니다.\n\n"
          "브랜드 폐점률은 브랜드별로 (계약종료 + 계약해지) ÷ (전년도 말 가맹점수 + 당해 신규 가맹점수)로 계산하고, "
          "상한 100%를 적용하며, 점수·순위표에는 최소 가맹점수 조건을 적용합니다.\n\n"
          "두 값은 집계 단위와 조건이 달라 직접 비교하지 않습니다."),
)

# ── 2. 등록 유지율 곡선 (자료 보기) ──────────────────────────────
st.subheader("업종별 등록 유지율")
group = st.radio("구분", ["전체", "법인", "개인"], horizontal=True, key="_w_ret_group")
st.plotly_chart(render_sector_retention(T["retention"], group), use_container_width=True)
st.caption("2021년에 등록된 브랜드를 기준으로 추적한 값입니다. (등록 시점 + 1~4년 뒤, 점 5개)")

# ── 3. 트리맵 (업종 선택 → 아래 지도, 후보 탐색으로 이어짐) ───────────
st.subheader(f"업종별 가맹점 수 ({year}년)")
st.plotly_chart(render_sector_treemap(T["treemap"], year, sector),
                use_container_width=True, on_select=_pick_sector, key=TM_KEY)
st.caption("칸의 크기는 가맹점 수입니다. 가맹점이 1개 이상인 브랜드 기준이며, 후보 탐색은 최소 가맹점수 조건을 적용합니다.")
st.caption("최소 가맹점수: 전년도 가맹점수가 이 값보다 적은 브랜드는 후보 탐색 대상에서 제외합니다. "
           "소규모 브랜드는 폐점률이 크게 흔들리기 때문이며, 왼쪽 필터에서 5·10·20개 중 고를 수 있습니다.")

c1, c2 = st.columns([3, 1])
c1.write(f"선택한 업종: **{sector}**" if sector else "선택한 업종: 없음 (트리맵에서 칸을 클릭하세요)")
if sector:
    c2.button("선택 해제", on_click=_clear_sector)

# ── 4. 시도별 면적당 매출 지도 (선택한 업종 기준) ─────────────────
st.subheader("시도별 면적당 평균 매출")
if year < 2022:
    st.info("면적당 매출 자료는 2022년부터 있습니다. 왼쪽 필터에서 2022년 이후를 선택해 주세요.")
elif not sector:
    st.info("위 트리맵에서 업종을 클릭하면 시도별 지도가 나타납니다.")
else:
    st.plotly_chart(render_region_map(T["region"], load_geo(), year, sector),
                    use_container_width=True)
    st.caption("지도를 드래그하면 확대되고, 더블클릭하면 전국 지도로 돌아옵니다.")
    st.caption(
        "회색은 자료가 없는 시도입니다. 면적 기준은 확인 중이며, 이상치로 판단한 값은 결측으로 처리했습니다.",
        help=("이상치 판단 기준: 같은 업종(중분류)의 2022~2025년 시도별 값 전체의 중앙값보다 10배 이상 큰 값은 "
              "이상치로 보고 자료 없음으로 처리했습니다.\n\n매출이 0으로 기록된 값도 자료 없음으로 처리했습니다."),
    )

render_footer()
