# ============================================================
# charts_sector.py  -  화면1(업종 현황) 차트 함수 모음
#   각 함수는 "표(DataFrame)를 받아 plotly Figure를 돌려주는" 형태
#   화면에 붙이는 일(st.plotly_chart)은 pages/1_업종현황.py에서 한다.
#   이름은 하늘님의 render_bubble / render_box 규칙에 맞춰 render_ 로 시작합니다.
# ============================================================
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 색: 시리즈 1 = 파랑(신규 등록률), 시리즈 2 = 주황(등록취소율)
# (색약 구분·대비 검사 통과한 색 조합)
BLUE   = "#2a78d6"
ORANGE = "#eb6834"
GRID   = "#e6e5e1"   # 눈금선
INK    = "#3d3d3a"   # 글자색

SECTOR_ORDER = ["외식", "서비스", "도소매"]   # 업종 대분류 표시 순서 (고정)

# 업종마다 색을 하나로 고정 (모든 차트에서 같은 업종 = 같은 색)
# 신규/취소 라인(파랑·주황)과 헷갈리지 않게 보라·초록·분홍 계열을 씀
SECTOR_COLORS = {"외식": "#6250d6", "서비스": "#008300", "도소매": "#e87ba4"}


def render_sector_trend(df: pd.DataFrame) -> go.Figure:
    """업종 대분류별 신규 등록률·등록취소율 연도 추이 (라인 3칸).

    df : data/sector_trend.parquet (컬럼: yr, sector, new_rate, cancel_rate, ...)
    칸 하나 = 업종 하나. 파란 선 = 신규 등록률, 주황 선 = 등록취소율.
    세로축은 세 칸이 같은 눈금이라 업종끼리 직접 비교할 수 있습니다.
    """
    fig = make_subplots(
        rows=1, cols=len(SECTOR_ORDER),
        shared_yaxes=True,                    # 세 칸의 세로 눈금을 같게
        subplot_titles=SECTOR_ORDER,
        horizontal_spacing=0.03,
    )

    for i, sector in enumerate(SECTOR_ORDER, start=1):
        d = df[df["sector"] == sector].sort_values("yr")
        for name, col, color in [("신규 등록률", "new_rate", BLUE),
                                 ("등록취소율",  "cancel_rate", ORANGE)]:
            fig.add_trace(
                go.Scatter(
                    x=d["yr"], y=d[col], name=name, mode="lines+markers",
                    line=dict(color=color, width=2),
                    marker=dict(color=color, size=7),
                    legendgroup=name,
                    showlegend=(i == 1),      # 범례는 한 번만
                    hovertemplate=name + " %{y:.1f}%<extra></extra>",
                ),
                row=1, col=i,
            )
        # 마지막 해 값만 선 끝에 표시 (모든 점에 숫자를 달면 복잡해짐)
        last = d.iloc[-1]
        gap = abs(last["new_rate"] - last["cancel_rate"])
        for col, color in [("new_rate", BLUE), ("cancel_rate", ORANGE)]:
            # 두 값이 가까우면 숫자가 겹치므로 위쪽 값은 위로, 아래쪽 값은 아래로 살짝 밀기
            up = last[col] >= max(last["new_rate"], last["cancel_rate"])
            shift = (0 if gap >= 3 else (9 if up else -9))
            fig.add_annotation(
                x=last["yr"], y=last[col], text=f"{last[col]:.1f}%",
                xref=f"x{i}" if i > 1 else "x", yref="y",
                showarrow=False, xanchor="left", xshift=8, yshift=shift,
                font=dict(size=11, color=INK),
            )

    # 눈금은 2017·2019·…·2025만, 오른쪽 여백은 끝 숫자가 들어갈 만큼만
    fig.update_xaxes(tickvals=[2017, 2019, 2021, 2023, 2025], range=[2016.2, 2026.6],
                     showgrid=False, tickfont=dict(color=INK))
    fig.update_yaxes(gridcolor=GRID, ticksuffix="%", tickfont=dict(color=INK),
                     rangemode="tozero", zeroline=False)
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=70, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", x=0, y=1.18, xanchor="left"),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color=INK),
    )
    return fig


def render_sector_retention(df: pd.DataFrame, group: str = "전체") -> go.Figure:
    """업종별 등록 유지율 곡선. 2021년에 등록한 브랜드가 N년 뒤에도 남아 있는 비율.

    df    : data/sector_retention.parquet
            (컬럼: sector, year_n, cal_year, base_cnt, kept_cnt, rate, group)
    group : "전체" / "법인" / "개인"  (브랜드 운영 본사의 사업자 형태)
    선 하나 = 업종 하나. 연차 0(등록 직후)은 100%에서 시작합니다.
    """
    d_all = df[df["group"] == group]
    fig = go.Figure()
    ends = []   # (업종, 마지막 연차 값) 선 끝 라벨용

    for sector in SECTOR_ORDER:
        d = d_all[d_all["sector"] == sector].sort_values("year_n")
        color = SECTOR_COLORS[sector]
        fig.add_trace(go.Scatter(
            x=d["year_n"], y=d["rate"], name=sector, mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(color=color, size=8),
            customdata=d[["cal_year", "kept_cnt", "base_cnt"]].values,
            hovertemplate=("%{customdata[0]}년 · 유지율 %{y:.1f}%<br>"
                           "%{customdata[1]:,}개 / %{customdata[2]:,}개<extra>" + sector + "</extra>"),
        ))
        ends.append((sector, float(d.iloc[-1]["rate"])))

    # 선 끝 라벨: 값이 가까우면 글자가 겹치므로, 위에서부터 최소 간격(MIN_GAP)을 두고 배치
    MIN_GAP = 4.0
    ends.sort(key=lambda t: -t[1])
    label_y, prev = {}, None
    for sector, val in ends:
        y = val if prev is None else min(val, prev - MIN_GAP)
        label_y[sector] = y
        prev = y
    x_last = d_all["year_n"].max()
    for sector, val in ends:
        fig.add_annotation(
            x=x_last, y=label_y[sector], text=f"{sector} {val:.1f}%",
            showarrow=False, xanchor="left", xshift=12,
            font=dict(size=12, color=INK),
        )

    fig.update_xaxes(
        tickvals=[0, 1, 2, 3, 4],
        ticktext=["등록 시점 (2021)", "1년 뒤 (2022)", "2년 뒤 (2023)", "3년 뒤 (2024)", "4년 뒤 (2025)"],
        range=[-0.2, 5.0], showgrid=False, tickfont=dict(color=INK),
    )
    fig.update_yaxes(
        range=[25, 102], ticksuffix="%", gridcolor=GRID, zeroline=False,
        tickfont=dict(color=INK), title_text="등록 시점 대비 남아 있는 브랜드 비율",
    )
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=30, b=40),
        hovermode="closest",
        legend=dict(orientation="h", x=0, y=1.1, xanchor="left"),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(color=INK),
    )
    return fig


def render_sector_treemap(df: pd.DataFrame, year: int, selected: str | None = None) -> go.Figure:
    """업종 대분류 → 중분류별 가맹점 수 트리맵.

    df       : data/sector_treemap.parquet (컬럼: yr, sector, mid_sector, brand_cnt, store_cnt)
    year     : 기준 연도 (사이드바의 기준 연도)
    selected : 선택된 업종 중분류 이름 (없으면 None). 선택된 칸은 굵은 테두리로 표시하고
               나머지는 살짝 옅게 보여 줌.
    칸의 크기 = 가맹점 수, 색 = 업종 대분류(고정색).
    """
    d = df[df["yr"] == year].copy()

    ids, labels, parents, values, colors, custom = [], [], [], [], [], []
    line_w, line_c, text_c = [], [], []
    for sector in SECTOR_ORDER:
        ds = d[d["sector"] == sector]
        base = SECTOR_COLORS[sector]
        # 도소매의 분홍은 밝아서 흰 글씨가 안 보임 → 글자색을 어둡게
        txt = INK if sector == "도소매" else "white"

        # 대분류 칸 (부모)
        ids.append(sector); labels.append(sector); parents.append("")
        values.append(0); colors.append(base); text_c.append(txt)
        custom.append([int(ds["store_cnt"].sum()), int(ds["brand_cnt"].sum())])
        line_w.append(2); line_c.append("white")

        # 중분류 칸 (자식). id는 '대분류/중분류'로 겹치지 않게
        for _, r in ds.iterrows():
            is_sel = (selected is not None and r["mid_sector"] == selected)
            ids.append(f"{sector}/{r['mid_sector']}")
            labels.append(r["mid_sector"]); parents.append(sector)
            values.append(int(r["store_cnt"]))
            colors.append(base); text_c.append(txt)
            custom.append([int(r["store_cnt"]), int(r["brand_cnt"])])
            line_w.append(5 if is_sel else 2)
            line_c.append(INK if is_sel else "white")

    # 선택된 칸이 있으면 나머지를 옅게
    opacity = 1.0 if selected is None else 0.55
    if selected is not None:
        sel_ids = {i for i in ids if i.endswith("/" + selected)}
        # 선택된 칸만 진하게 하려면 색 대신 투명도 배열을 쓸 수 없어서, 색을 직접 옅게 섞음
        def fade(hexc):
            r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
            return "#%02x%02x%02x" % tuple(int(c * 0.72 + 255 * 0.28) for c in (r, g, b))
        colors = [c if (i in sel_ids or "/" not in i) else fade(c) for i, c in zip(ids, colors)]

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="remainder",
        marker=dict(colors=colors, line=dict(color=line_c, width=line_w)),
        customdata=custom,
        hovertemplate="<b>%{label}</b><br>가맹점 %{customdata[0]:,}개<br>"
                      "브랜드 %{customdata[1]:,}개<extra></extra>",
        texttemplate="%{label}<br>%{value:,}",
        textfont=dict(color=text_c, size=13),
        pathbar=dict(visible=False),
        tiling=dict(pad=3),
        level="",                 # 항상 맨 위(전체)에서 시작
    ))
    fig.update_layout(height=460, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor="white", font=dict(color=INK))
    return fig


# ------------------------------------------------------------
# 시도별 면적당 매출 지도
# ------------------------------------------------------------
# region_sales의 시도 이름(짧은 이름)  →  경계 파일(sido_geo.json)의 이름
SIDO_FULL = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전라북도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}
NO_DATA = "#d9d8d3"   # 자료 없는 시도는 회색으로


def _polygon_xy(geometry):
    """경계(GeoJSON geometry)의 바깥선들을 하나의 x, y 목록으로 (조각 사이는 None으로 끊음)"""
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    xs, ys = [], []
    for poly in polys:
        ring = poly[0]                       # 바깥 테두리만 사용
        xs += [p[0] for p in ring] + [None]
        ys += [p[1] for p in ring] + [None]
    return xs, ys


def render_region_map(df: pd.DataFrame, geojson: dict, year: int, mid_sector: str) -> go.Figure:
    """시도별 면적당 평균 매출 지도 (진한 파랑일수록 매출이 큼, 회색 = 자료 없음).

    df         : data/region_sales.parquet (컬럼: yr, sector, mid_sector, area, sales_per_area)
    geojson    : data/sido_geo.json (시도 경계, 이름이 properties.name)
    year       : 기준 연도 (2022~2025만 자료가 있음)
    mid_sector : 업종 중분류 (예: "편의점")

    외부 지도 서버 없이 경계선을 직접 그리는 방식이라 인터넷이 막힌 환경에서도 동작함.
    """
    from plotly.colors import sample_colorscale

    scale = [[0, "#e3eefb"], [0.5, "#6fa6e6"], [1, "#0b3d82"]]   # 연한 파랑 → 진한 파랑
    d = df[(df["yr"] == year) & (df["mid_sector"] == mid_sector)]
    val = {SIDO_FULL[a]: v for a, v in zip(d["area"], d["sales_per_area"]) if a in SIDO_FULL}
    nums = [v for v in val.values() if pd.notna(v)]
    vmin, vmax = (min(nums), max(nums)) if nums else (0, 1)

    fig = go.Figure()
    for feat in geojson["features"]:
        name = feat["properties"]["name"]
        short = next((k for k, v in SIDO_FULL.items() if v == name), name)
        v = val.get(name)
        if v is None or pd.isna(v):
            color, tip = NO_DATA, f"{short}<br>자료 없음"
        else:
            t = 0.5 if vmax == vmin else (v - vmin) / (vmax - vmin)
            color = sample_colorscale(scale, [t])[0]
            tip = f"{short}<br>면적당 평균 매출 {v:,.0f}"
        xs, ys = _polygon_xy(feat["geometry"])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=color,
            line=dict(color="white", width=1), hoveron="fills",
            text=tip, hoverinfo="text", showlegend=False,
        ))

    # 색 막대(범례)용: 화면에는 보이지 않는 점 하나
    if nums:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
            marker=dict(colorscale=scale, cmin=vmin, cmax=vmax, showscale=True,
                        color=[vmin], size=0,
                        colorbar=dict(title=dict(text="면적당 평균 매출", side="right"),
                                      thickness=14, len=0.7, tickformat=",.0f", outlinewidth=0)),
        ))

    # 회색 칸의 뜻을 알려 주는 범례 (자료 없는 시도가 있을 때만)
    if any(v is None or pd.isna(v) for v in [val.get(f["properties"]["name"]) for f in geojson["features"]]):
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper", showarrow=False, xanchor="left",
            text=f'<span style="color:{NO_DATA}">■</span> 회색 = 자료 없음',
            font=dict(size=12, color=INK),
        )

    fig.update_xaxes(visible=False, range=[124.5, 130.2])
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.24, range=[32.9, 38.7])
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0),
                      plot_bgcolor="white", paper_bgcolor="white", font=dict(color=INK))
    return fig
