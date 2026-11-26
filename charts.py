import numpy as np
import pandas as pd
import plotly.graph_objects as go

INK = "#3d3d3a"
GRID = "#e6e5e1"

# 창업비용·평균 매출의 단위는 천원. 눈금 글자는 읽기 쉽게 만원/억으로 표시
_TICKS = [3000, 10000, 30000, 100000, 300000, 1000000, 3000000]
_TICK_TEXT = ["300만", "1천만", "3천만", "1억", "3억", "10억", "30억"]


def _won(v):
    """천원 단위 숫자를 '1억 2,300만원' 형태 글자로"""
    man = v / 10  # 만원
    if man >= 10000:
        eok, rest = divmod(man, 10000)
        return f"{int(eok)}억 {int(round(rest)):,}만원" if round(rest) else f"{int(eok)}억원"
    return f"{int(round(man)):,}만원"


def _range(s, pad=0.8):
    """상·하위 1%를 자른 로그축 표시 범위"""
    if len(s) >= 20:
        lo, hi = s.quantile(0.01), s.quantile(0.99)
    else:
        lo, hi = s.min(), s.max()
    return [np.log10(lo * pad), np.log10(hi / pad)]


def render_bubble(df, score_col="score"):
    """화면2 버블 차트: x=창업비용, y=매출 배수, 크기=가맹점수, 색=종합 점수."""
    Y_LO, Y_HI = 0.17, 23.16      # 매출 배수 표시 범위 (밖의 값은 잘라서 표시)
    X_LO, X_HI = 4000, 600000     # 창업비용 표시 범위 (천원)

    def money(v):  # 단위: 천원
        return f"{v / 100_000:.2f}억원" if v >= 100_000 else f"{v / 10:,.0f}만원"

    d = df.dropna(subset=["smtnAmt", "sales_multiple", "frcsCnt"]).copy()
    d = d[(d["smtnAmt"] > 0) & (d["frcsCnt"] > 0)]
    has_score = score_col in d.columns
    if has_score:
        d = d.dropna(subset=[score_col])

    fig = go.Figure()
    if len(d) == 0:
        return fig

    x = d["smtnAmt"].clip(X_LO, X_HI)
    y = d["sales_multiple"].clip(Y_LO, Y_HI)
    size = d["frcsCnt"].clip(upper=d["frcsCnt"].quantile(0.99))
    sizeref = 2.0 * size.max() / (28 ** 2)

    names = d["brandNm"] if "brandNm" in d.columns else [""] * len(d)
    sectors = d["indutyMlsfcNm"] if "indutyMlsfcNm" in d.columns else [""] * len(d)
    hover = [
        f"<b>{n}</b> ({s})<br>창업비용 {money(a)}<br>매출 배수 {m:.2f}배<br>가맹점수 {int(f):,}개"
        + (f"<br>종합 점수 {sc:.1f}" if has_score else "")
        for n, s, a, m, f, sc in zip(
            names, sectors, d["smtnAmt"], d["sales_multiple"], d["frcsCnt"],
            d[score_col] if has_score else [0] * len(d))
    ]

    marker = dict(
        size=size, sizemode="area", sizeref=sizeref, sizemin=4,
        opacity=0.7, line=dict(width=0.5, color="white"),
    )
    if has_score:
        marker.update(color=d[score_col], colorscale=[[0, "#cfe0f5"], [1, "#0f3d7a"]],
                      cmin=0, cmax=100, showscale=True,
                      colorbar=dict(title="종합 점수", thickness=12, len=0.75, y=0.4))
    else:
        marker.update(color="#2a78d6")

    # 데이터에 맞춘 축 범위
    y_top = min(Y_HI, float(y.max()) * 1.2) + 0.5
    x_lo = max(X_LO, float(x.min()) * 0.8)
    x_hi = min(X_HI, float(x.max()) * 1.25)

    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=marker,
                             hovertext=hover, hoverinfo="text", showlegend=False))

    fig.update_layout(
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color="#3d3d3a", size=13),
        xaxis=dict(type="log", range=[np.log10(x_lo), np.log10(x_hi)],
                   tickvals=[5000, 7000, 10000, 20000, 30000, 50000, 70000, 100000, 150000, 200000, 300000, 500000],
                   ticktext=["500만", "700만", "1천만", "2천만", "3천만", "5천만", "7천만", "1억", "1.5억", "2억", "3억", "5억"],
                   title="창업비용", gridcolor="#e6e5e1", zeroline=False),
        yaxis=dict(range=[0, y_top], title="매출 배수", ticksuffix="배",
                   gridcolor="#e6e5e1", zeroline=False),
    )
    return fig


def render_box(df: pd.DataFrame, top_n: int = 12) -> go.Figure:
    """업종 중분류별 창업비용 분포 박스플롯.

    df : 브랜드 표. 필요한 컬럼 brandNm, indutyMlsfcNm, smtnAmt
    업종이 여러 개면 브랜드 수가 많은 상위 top_n개만 표시.
    """
    d = df.dropna(subset=["smtnAmt"])
    d = d[d["smtnAmt"] > 0]

    fig = go.Figure()
    if d.empty:
        fig.update_layout(height=320, annotations=[dict(text="표시할 브랜드가 없습니다", showarrow=False)])
        return fig

    counts = d["indutyMlsfcNm"].value_counts()
    keep = list(counts.index[:top_n])
    d = d[d["indutyMlsfcNm"].isin(keep)]
    # 중앙값이 큰 업종이 위로 오도록 정렬
    order = d.groupby("indutyMlsfcNm")["smtnAmt"].median().sort_values().index.tolist()

    fig.add_trace(go.Box(
        x=d["smtnAmt"], y=d["indutyMlsfcNm"], orientation="h",
        marker=dict(color="#2a78d6", size=4), line=dict(color="#2a78d6", width=1.5),
        fillcolor="rgba(42,120,214,0.25)", boxpoints="outliers",
        customdata=d[["brandNm"]].values,
        hovertemplate="%{customdata[0]}<br>창업비용 %{x:,.0f}천원<extra></extra>",
        showlegend=False,
    ))

    fig.update_xaxes(type="log", range=_range(d["smtnAmt"], pad=0.8),
                     tickvals=_TICKS, ticktext=_TICK_TEXT, title_text="창업비용",
                     gridcolor=GRID, zeroline=False, tickfont=dict(color=INK))
    fig.update_yaxes(categoryorder="array", categoryarray=order, tickfont=dict(color=INK))
    fig.update_layout(height=max(220, 60 + 34 * len(order)), margin=dict(l=10, r=10, t=10, b=40),
                      plot_bgcolor="white", paper_bgcolor="white", font=dict(color=INK))
    return fig