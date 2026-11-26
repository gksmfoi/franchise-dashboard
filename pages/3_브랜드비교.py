"""
화면3 브랜드 비교 (D 담당)

- 비교 대상은 st.session_state[COMPARE_SET]에서 읽기만 한다. (설정은 화면2)
- 비교 지역(REGION)은 이 화면의 render_region_select()에서만 바꾼다.
- DEV_MODE=True로 바꾸면 담은 브랜드가 없을 때 개발용 임시 선택 상자가 나온다.
  이 선택 상자는 상태 키를 바꾸지 않고 이 화면 안에서만 쓴다.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common.data import load_data, get_region_baseline
from common.sidebar import render_sidebar, render_region_select, MIN_YEAR
from common.footer import render_footer
from common.state import (COMPARE_SET, MAX_COMPARE, MIN_STORES, WEIGHTS, YEAR,
                          init_state, make_brand_id)
from metrics import compute_score

st.set_page_config(page_title="브랜드 비교", layout="wide")
init_state()
df = load_data()
render_sidebar(df)

year = st.session_state[YEAR]
min_stores = st.session_state[MIN_STORES]
weights = st.session_state[WEIGHTS]

# ── 설정 ───────────────────────────────────────────────
DEV_MODE = False   # 화면2 '비교에 담기' 완성 후 False로 변경
DEV_DEFAULT = [
    "교촌에프앤비(주)|교촌치킨|치킨",
    "(주)지앤푸드|굽네치킨|치킨",
    "(주)한국일오삼|처갓집양념치킨|치킨",
    "다이닝브랜즈그룹(주)|비에이치씨(BHC)|치킨",
]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # 비교 순서대로 고정
AXES = [  # (pct 컬럼, 원래 값 컬럼, 축 이름)
    ("pct_closure", "closure_rate", "낮은 폐점률"),
    ("pct_growth", "net_growth", "순성장률"),
    ("pct_sales", "avrgSlsAmt", "평균 매출"),
    ("pct_multiple", "sales_multiple", "매출 배수"),
]


# ── 데이터 ─────────────────────────────────────────────
@st.cache_data
def brand_table():
    d = load_data().copy()
    d["brand_id"] = [make_brand_id(c, b, m) for c, b, m in
                     zip(d["corpNm"], d["brandNm"], d["indutyMlsfcNm"])]
    return d


@st.cache_data
def scores(year, min_stores, weight_items):
    return compute_score(brand_table(), year, min_stores, dict(weight_items))


bt = brand_table()
NG_CAP = bt["net_growth"].quantile(0.99)   # 순성장률 표시 상한 (정의서: 상위 1%)
cur = bt[bt["yr"] == year].set_index("brand_id")
sc = scores(year, min_stores, tuple(sorted(weights.items()))).set_index("brand_id")


# ── 표시 형식 ──────────────────────────────────────────
def pct(v):
    return "-" if pd.isna(v) else f"{v * 100:.1f}%"


def money(v):  # 단위: 천원
    if pd.isna(v):
        return "미제공"
    return f"{v / 100_000:.2f}억원" if v >= 100_000 else f"{v / 10:,.0f}만원"


def times(v):
    return "-" if pd.isna(v) else f"{v:.2f}배"


def label(bid):
    corp, brand, mid = bid.split("|")
    return f"{brand} ({mid} · {corp})"


def raw_text(col, v):
    if col in ("closure_rate", "net_growth"):
        return pct(v)
    if col == "avrgSlsAmt":
        return money(v)
    return times(v)


# ── 화면 ───────────────────────────────────────────────
st.title("브랜드 비교")
st.write(f"{year}년 기준, 최소 가맹점수 {min_stores}개 기준으로 비교합니다.")

with st.columns([1, 3])[0]:
    region = render_region_select()   # 아래 '면적당 평균 매출' 차트의 기준선 지역

selected = list(st.session_state[COMPARE_SET])
if not selected and DEV_MODE:
    st.warning("개발용 임시 선택입니다. 화면2의 '비교에 담기'가 완성되면 사라집니다.")
    options = sorted(cur.index)
    selected = st.multiselect(
        "비교 브랜드 (개발용, 최대 4개)",
        options,
        default=[b for b in DEV_DEFAULT if b in cur.index],
        max_selections=MAX_COMPARE,
        format_func=label,
        key="_w_dev_compare",
    )

if not selected:
    st.info("후보 탐색 화면에서 비교할 브랜드를 담아 주세요. (최대 4개)")
    render_footer()
    st.stop()

color_of = {bid: COLORS[i] for i, bid in enumerate(selected)}
name_of = {bid: bid.split("|")[1] for bid in selected}


# 1) 요약 카드 ----------------------------------------------------------
def score_reason(bid):
    """점수가 없을 때 이유"""
    if bid not in cur.index:
        return f"{year}년 자료 없음"
    prev = cur.loc[bid, "prevCnt"]
    if pd.isna(prev) or prev == 0:
        return "전년도 가맹점 자료 없음"
    if prev < min_stores:
        return f"전년도 가맹점 {prev:.0f}개로 최소 기준({min_stores}개) 미만"
    return "지표 중 결측이 있어 산출 불가"


cols = st.columns(len(selected))
for col, bid in zip(cols, selected):
    with col, st.container(border=True):
        corp, brand, mid = bid.split("|")
        row = cur.loc[bid] if bid in cur.index else None
        tags = []
        if row is not None and row["is_new_brand"]:
            tags.append(":orange-badge[신규]")
        if row is not None and pd.notna(row["prevCnt"]) and row["prevCnt"] < 10:
            tags.append(":gray-badge[소규모]")
        st.markdown(
            f"<span style='color:{color_of[bid]};font-size:1.2em'>●</span> **{brand}** "
            + " ".join(tags),
            unsafe_allow_html=True)
        st.caption(f"{mid} · {corp}")

        if row is None:
            st.write(f"{year}년 자료가 없습니다.")
            continue

        has_score = bid in sc.index and pd.notna(sc.loc[bid, "score"])
        st.metric(
            "종합 점수",
            f"{sc.loc[bid, 'score']:.1f}" if has_score else "산출 불가",
            help="업종 안에서 4개 지표의 백분위를 가중합한 값(0~100)입니다. 추천이 아니라 비교의 출발점입니다.",
        )
        if not has_score:
            st.caption(score_reason(bid))

        st.markdown(
            f"- 가맹점수: {row['frcsCnt']:,.0f}개\n"
            f"- 폐점률: {pct(row['closure_rate'])}\n"
            f"- 순성장률: {pct(row['net_growth'])}\n"
            f"- 평균 매출: {money(row['avrgSlsAmt'])}\n"
            f"- 창업비용: {money(row['smtnAmt'])}\n"
            f"- 매출 배수: {times(row['sales_multiple'])}"
        )

st.caption(
    "폐점률 = (계약종료 + 계약해지) ÷ (전년도 말 가맹점수 + 당해 신규 가맹점수), 순성장률 = "
    "(신규 − 계약종료 − 계약해지) ÷ 전년도 말 가맹점수. 두 지표는 분모가 다릅니다. "
    "매출은 이익이 아니므로 매출 배수를 투자회수기간으로 해석하지 않습니다."
)

left, right = st.columns(2)

# 2) 레이더 차트 --------------------------------------------------------
with left:
    st.subheader("지표별 백분위")
    radar = go.Figure()
    groups = set()
    for bid in selected:
        if bid not in sc.index or pd.isna(sc.loc[bid, "score"]):
            continue
        r = sc.loc[bid]
        groups.add(r["rank_group"])
        vals = [r[p] * 100 for p, _, _ in AXES]
        hover = [f"{name_of[bid]}<br>{a}: 백분위 {v:.0f}<br>실제 값 {raw_text(c, r[c])}"
                 for (_, c, a), v in zip(AXES, vals)]
        radar.add_trace(go.Scatterpolar(
            r=vals + vals[:1],
            theta=[a for _, _, a in AXES] + [AXES[0][2]],
            name=name_of[bid],
            mode="lines+markers",
            line=dict(color=color_of[bid], width=2),
            marker=dict(size=8),
            hovertext=hover + hover[:1], hoverinfo="text",
        ))
    if radar.data:
        radar.update_layout(
            polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], angle=45, tickangle=45)),
            legend=dict(orientation="h", y=-0.15),
            margin=dict(l=40, r=40, t=30, b=30), height=420,
        )
        st.plotly_chart(radar, width="stretch")
        st.caption("바깥쪽일수록 같은 업종 안에서 좋은 편입니다(백분위 0~100). 폐점률은 낮을수록 바깥쪽에 표시됩니다.")
        if len(groups) > 1:
            st.warning(f"비교 브랜드의 순위 기준 업종이 서로 다릅니다({', '.join(sorted(groups))}). "
                       "백분위는 각 업종 안에서의 순위라 직접 비교에 주의해 주세요.")
    else:
        st.info("현재 기준에서 점수를 산출할 수 있는 브랜드가 없습니다.")

# 3) 추이 라인 ----------------------------------------------------------
with right:
    st.subheader(f"추이 ({MIN_YEAR}~{bt['yr'].max()}년)")
    tab1, tab2 = st.tabs(["폐점률", "순성장률"])
    hist = bt[bt["brand_id"].isin(selected) & (bt["yr"] >= MIN_YEAR)]

    def line_chart(col, title, cap=None):
        fig = go.Figure()
        clipped = False
        for bid in selected:
            h = hist[hist["brand_id"] == bid].sort_values("yr")
            y = h[col] * 100
            if cap is not None:
                clipped |= bool((h[col] > cap).any())
                y = y.clip(upper=cap * 100)
            fig.add_trace(go.Scatter(
                x=h["yr"], y=y, name=name_of[bid], mode="lines+markers",
                line=dict(color=color_of[bid], width=2), marker=dict(size=8),
                customdata=[pct(v) for v in h[col]],
                hovertemplate=f"{name_of[bid]}: %{{customdata}}<extra></extra>",
            ))
        fig.add_vline(x=year, line=dict(color="#9a9893", width=1, dash="dot"))
        fig.update_layout(
            yaxis=dict(title=title, ticksuffix="%"),
            xaxis=dict(dtick=1),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
            margin=dict(l=40, r=20, t=30, b=30), height=380,
        )
        st.plotly_chart(fig, width="stretch")
        if clipped:
            st.caption(f"{title}이 {cap * 100:.0f}%를 넘는 값은 그래프에서 {cap * 100:.0f}%로 잘라 표시했습니다. "
                       "마우스를 올리면 실제 값이 보입니다.")

    with tab1:
        line_chart("closure_rate", "폐점률")
    with tab2:
        line_chart("net_growth", "순성장률", cap=NG_CAP)

    short = [name_of[b] for b in selected
             if hist.loc[hist["brand_id"] == b, "closure_rate"].notna().sum() < 3]
    if short:
        st.caption(f"{', '.join(short)}: 관측 연도가 짧아 선이 짧게 표시됩니다.")
    st.caption("법인명이 바뀐 브랜드는 추이 그래프가 변경 이후 연도부터만 표시될 수 있습니다. "
               "점수와 신규 여부는 이전 기록을 이어서 계산합니다.")


# 4) 면적당 평균 매출 + 지역 기준선 ---------------------------------------
REGION_MIN_YEAR = 2022   # region_sales는 2022년부터 있음
BASE_COLOR = "#3d3d3a"

st.subheader("면적당 평균 매출")

rows = []
for bid in selected:
    corp, brand, mid = bid.split("|")
    v = cur.loc[bid, "arUnitAvrgSlsAmt"] if bid in cur.index else float("nan")
    base = (get_region_baseline(year, mid, region)
            if region and year >= REGION_MIN_YEAR else None)
    rows.append(dict(bid=bid, name=name_of[bid], mid=mid, value=v, base=base))
bar = pd.DataFrame(rows)

fig = go.Figure()
# 브랜드 막대 (전국 가맹점 평균, 비교 순서대로 같은 색)
fig.add_trace(go.Bar(
    x=bar["name"], y=bar["value"],
    marker_color=[color_of[b] for b in bar["bid"]],
    customdata=bar["mid"],
    hovertemplate="%{x} (%{customdata})<br>면적당 평균 매출 %{y:,.0f}<extra></extra>",
    showlegend=False,
))
# 지역 기준선: 막대마다 그 브랜드 업종의 시도 평균을 짧은 가로선으로 표시
has_base = bar["base"].notna()
if has_base.any():
    b = bar[has_base]
    fig.add_trace(go.Scatter(
        x=b["name"], y=b["base"], mode="markers",
        marker=dict(symbol="line-ew-open", size=70, line=dict(color=BASE_COLOR, width=3)),
        name=f"{region} 업종 평균 (기준선)",
        customdata=b["mid"],
        hovertemplate=f"{region} " + "%{customdata} 평균 %{y:,.0f}<extra></extra>",
    ))

# 값이 없을 때 막대 위에 이유 표시
ymax = pd.concat([bar["value"], bar["base"].astype(float)]).max()
ymax = 1 if pd.isna(ymax) else ymax
for _, r in bar.iterrows():
    notes = []
    if pd.isna(r["value"]):
        notes.append("매출 자료 미제공")
    if region and year >= REGION_MIN_YEAR and pd.isna(r["base"]):
        notes.append("기준선 자료 없음")
    if notes:
        top = r["value"] if pd.notna(r["value"]) else 0
        fig.add_annotation(x=r["name"], y=top, text="<br>".join(notes), showarrow=False,
                           yshift=18, font=dict(size=12, color="#6b6a65"))

fig.update_layout(
    yaxis=dict(title="면적당 평균 매출 (천원)", range=[0, ymax * 1.2], gridcolor="#e6e5e1"),
    legend=dict(orientation="h", y=1.12, x=0),
    bargap=0.45, plot_bgcolor="white",
    margin=dict(l=40, r=20, t=40, b=30), height=380,
)
st.plotly_chart(fig, width="stretch")

if not region:
    st.caption("위의 '비교 지역'에서 시도를 고르면 그 지역·업종의 평균이 기준선으로 표시됩니다.")
elif year < REGION_MIN_YEAR:
    st.caption(f"지역 기준선 자료는 {REGION_MIN_YEAR}년부터 있습니다. 기준 연도를 {REGION_MIN_YEAR}년 이후로 바꿔 주세요.")
st.caption(
    "막대는 브랜드의 전국 가맹점 면적당 평균 매출이고, 기준선은 선택한 시도에서 같은 업종의 평균입니다. "
    "업종이 다른 브랜드는 각자 업종의 기준선을 씁니다. 면적 기준은 확인 중입니다.",
    help="기준선(시도·업종 평균)은 같은 업종 브랜드들의 중앙값보다 대체로 높게 나옵니다. "
         "기준선보다 낮다고 해서 그 브랜드가 나쁘다는 뜻은 아닙니다.",
)

st.caption("자료: 공정거래위원회 가맹사업정보. 점선은 선택한 기준 연도입니다.")

render_footer()
