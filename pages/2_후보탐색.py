import pandas as pd
import streamlit as st
from common.state import (init_state, YEAR, MIN_STORES, HIDE_NEW, SECTOR, BUDGET_RANGE,
                          COMPARE_SET, MAX_COMPARE, WEIGHTS, DEFAULTS, add_compare, make_brand_id)
from common.data import load_data, get_scores
from common.sidebar import render_sidebar
from common.footer import render_footer
from charts import render_bubble, render_box

st.set_page_config(page_title="후보 탐색", layout="wide")
init_state()
df = load_data()
render_sidebar(df)

st.title("후보 탐색")

result = get_scores(st.session_state[YEAR], st.session_state[MIN_STORES],
                    tuple(sorted(st.session_state[WEIGHTS].items())))

def _sync_hide_new():
    st.session_state[HIDE_NEW] = st.session_state["_w_hide_new"]


def _sync_budget():
    st.session_state[BUDGET_RANGE] = tuple(v * 10 for v in st.session_state["_w_budget"])


st.checkbox(
    "신규 브랜드 제외 (관측 3년 미만)",
    value=st.session_state[HIDE_NEW],
    key="_w_hide_new",
    on_change=_sync_hide_new,
)

_b_lo, _b_hi = st.session_state[BUDGET_RANGE]
st.slider("창업비용 범위 (만원)", 0, 50000, (_b_lo // 10, _b_hi // 10), step=500,
          key="_w_budget", on_change=_sync_budget)
def _fmt_won(man):
    return f"{man / 10000:g}억" if man >= 10000 else f"{man:,}만원"

_hi_txt = "상한 없음" if _b_hi >= 500_000 else _fmt_won(_b_hi // 10)
st.caption(f"선택한 범위: {_fmt_won(_b_lo // 10)} ~ {_hi_txt}  (오른쪽 끝(5억)에 두면 상한 없이 모두 보여 줍니다.)")


W_KEYS = [("closure", "폐점률 (낮을수록 높은 점수)"), ("growth", "순성장률"),
          ("sales", "가맹점 평균 매출"), ("multiple", "초기비용 대비 매출 배수")]


def _sync_weights():
    new = {k: st.session_state[f"_w_wt_{k}"] / 100 for k, _ in W_KEYS}
    if sum(new.values()) > 0:          # 전부 0이면 점수를 만들 수 없어 반영하지 않음
        st.session_state[WEIGHTS] = new


def _reset_weights():
    st.session_state[WEIGHTS] = dict(DEFAULTS[WEIGHTS])
    for k, _ in W_KEYS:
        st.session_state[f"_w_wt_{k}"] = round(DEFAULTS[WEIGHTS][k] * 100)


with st.expander("지표 가중치 조절 (종합 점수에 반영)"):
    st.caption("각 지표를 얼마나 중요하게 볼지 정합니다. 합계가 100이 아니어도 비율로 환산해 계산합니다.")
    wcols = st.columns(4)
    for col, (k, name) in zip(wcols, W_KEYS):
        col.slider(name, 0, 100, round(st.session_state[WEIGHTS][k] * 100), step=5,
                   key=f"_w_wt_{k}", on_change=_sync_weights)
    _tot = sum(st.session_state[WEIGHTS].values())
    if sum(st.session_state[f"_w_wt_{k}"] for k, _ in W_KEYS) == 0:
        st.warning("가중치가 모두 0이면 점수를 계산할 수 없어 이전 값을 그대로 씁니다.")
    st.caption("적용된 비율: " + " · ".join(
        f"{name.split(' (')[0]} {st.session_state[WEIGHTS][k] / _tot * 100:.0f}%" for k, name in W_KEYS))
    st.button("기본값으로 되돌리기", on_click=_reset_weights)

if st.session_state[HIDE_NEW]:
    result = result[~result["is_new_brand"]]

sector = st.session_state[SECTOR]
if sector:
    result = result[result["indutyMlsfcNm"] == sector]
    st.info(f"화면1에서 선택한 업종: **{sector}** — 이 업종의 브랜드만 보여 줍니다. (해제는 '업종현황' 화면에서)")

_lo, _hi = st.session_state[BUDGET_RANGE]
if _lo > 0 or _hi < 500_000:
    result = result[result["smtnAmt"].between(_lo, _hi if _hi < 500_000 else float("inf"))]

st.write(f"대상 브랜드 {len(result):,}개, 점수 산출 가능 {result['score'].notna().sum():,}개")
st.caption("점수는 신규 브랜드를 포함한 업종 내 순위(백분위)로 계산됩니다. '신규 브랜드 제외'는 표에서만 거릅니다.")
if len(result) > 0:
    tab1, tab2 = st.tabs(["브랜드 분포 (버블)", "업종별 분포 (상자 그림)"])
    with tab1:
        st.plotly_chart(render_bubble(result), width="stretch")
        st.caption(
            "점 하나가 브랜드 하나입니다. 가로는 창업비용, 세로는 매출 배수, 크기는 가맹점수, 색은 종합 점수입니다. "
            "매출 배수는 0.17~23.16배 밖의 값을 잘라서 표시했고, 종합 점수를 산출한 브랜드만 표시합니다. "
            "매출 배수는 투자회수기간이 아닙니다."
        )
    with tab2:
        st.plotly_chart(render_box(result), width="stretch")
        st.caption("업종(중분류)별 창업비용 분포입니다. 상자의 가운데 선은 중앙값이고, 점은 일반 범위를 벗어난 브랜드입니다.")
        
top = result.head(50).copy()
ids = [make_brand_id(c, b, m) for c, b, m in
       zip(top["corpNm"], top["brandNm"], top["indutyMlsfcNm"])]


def flag(row):
    tags = []
    if row["prevCnt"] < 10:
        tags.append("소규모")
    if row["is_new_brand"]:
        tags.append("신규")
    return ", ".join(tags)


show = pd.DataFrame({
    "순위": range(1, len(top) + 1),
    "브랜드": top["brandNm"].values,
    "업종": top["indutyMlsfcNm"].values,
    "점수": top["score"].values,
    "가맹점수": top["frcsCnt"].values,
    "폐점률(%)": top["closure_rate"].values * 100,
    "순성장률(%)": top["net_growth"].values * 100,
    "매출배수": top["sales_multiple"].values,
    "표시": top.apply(flag, axis=1).values,
})

event = st.dataframe(
    show, width="stretch", hide_index=True,
    column_config={
        "점수": st.column_config.NumberColumn(format="%.1f"),
        "폐점률(%)": st.column_config.NumberColumn(format="%.1f"),
        "순성장률(%)": st.column_config.NumberColumn(format="%.1f"),
        "매출배수": st.column_config.NumberColumn(format="%.1f"),
    },
    on_select="rerun",
    selection_mode="multi-row",
    key="_w_rank_table",
)
picked = [ids[i] for i in event.selection.rows]

cur_set = list(st.session_state[COMPARE_SET])
c1, c2 = st.columns([1, 1])
with c1:
    if st.button("선택한 브랜드를 비교에 담기", disabled=not picked):
        new = [b for b in picked if b not in cur_set]
        room = MAX_COMPARE - len(cur_set)
        for b in new[:room]:
            add_compare(b)
        if len(new) > room:
            st.warning(f"비교는 최대 {MAX_COMPARE}개까지 담을 수 있어 {room}개만 담았습니다.")
        if len(new) <= room:
            st.rerun()
with c2:
    if st.button("비교 목록 비우기", disabled=not cur_set):
        st.session_state[COMPARE_SET] = []
        st.rerun()

cur_set = list(st.session_state[COMPARE_SET])
if cur_set:
    st.write("비교 목록: " + ", ".join(b.split("|")[1] for b in cur_set)
             + f" ({len(cur_set)}/{MAX_COMPARE})")
    st.caption("왼쪽 메뉴의 '브랜드비교'에서 확인할 수 있습니다.")

render_footer()