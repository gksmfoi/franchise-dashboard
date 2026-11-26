import glob
import streamlit as st
from common.state import init_state
from common.footer import render_footer

st.set_page_config(page_title="프랜차이즈 건전성 대시보드", layout="wide")
init_state()


def _page(n):
    return sorted(glob.glob(f"pages/{n}_*.py"))[0]


st.title("프랜차이즈 가맹사업 건전성 대시보드")
st.write(
    "예비 창업자를 위한 참고용 대시보드로 예산과 희망 업종에 맞는 프랜차이즈 브랜드를 공공데이터로 비교해 볼 수 있습니다."
)

st.write("")
c1, c2, c3 = st.columns(3)

cards = [
    (c1, 1, "업종 현황", "업종별 가맹점 수와 등록 추이를 보고 관심 업종을 고릅니다.", "업종 현황 열기"),
    (c2, 2, "후보 탐색", "예산과 업종에 맞는 브랜드를 건전성 점수 순으로 보고 비교할 브랜드를 담습니다.", "후보 탐색 열기"),
    (c3, 3, "브랜드 비교", "담은 브랜드의 폐점률, 순성장률, 매출을 같은 업종 안에서 나란히 비교합니다.", "브랜드 비교 열기"),
]
for col, n, title, desc, label in cards:
    with col:
        with st.container(border=True, height=220):
            st.subheader(title)
            st.write(desc)
            st.page_link(_page(n), label=label, width="stretch")

st.write("")
st.caption(
    "자료: 공정거래위원회 가맹사업정보"
)

render_footer()
