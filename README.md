# 프랜차이즈 가맹사업 건전성 대시보드

예비 창업자의 브랜드 선택을 돕는 참고용 대시보드입니다. (고급데이터시각화 1팀)
공정위 프랜차이즈 가맹사업 정보를 사용하며 점수와 지표는 특정 브랜드를 추천하는 것이 아니라 비교의 출발점입니다.

## 1. 폴더 구조

```
franchise-app/
├─ 홈.py                 시작 화면
├─ metrics.py             점수 계산 (compute_score) - B 담당
├─ charts.py              차트 함수 (render_bubble, render_box) - C 담당
├─ charts_sector.py       화면1 차트 함수 (트리맵, 지도, 추이, 유지율) - A 담당
├─ requirements.txt       배포·설치용 패키지 목록
├─ .streamlit/config.toml  테마 설정 (위젯 색상)
├─ common/
│  ├─ state.py            session_state 키 정의·초기화 (아래 3번 규칙)
│  ├─ data.py             데이터 불러오기·점수 계산 (캐시, 가중치 반영)
│  ├─ footer.py           모든 화면 하단의 데이터 해석 유의사항 (render_footer)
│  └─ sidebar.py          모든 페이지 공통 사이드바 (연도, 최소 가맹점수)
├─ pages/
│  ├─ 1_업종현황.py       화면1 (구현 완료 - A 담당)
│  ├─ 2_후보탐색.py       화면2 (순위표, 신규 제외, 업종·창업비용 필터, 지표 가중치 슬라이더, 버블·상자 그림 차트 탭 구현 완료 - B 담당)
│  └─ 3_브랜드비교.py     화면3 (구현 완료 - D 담당)
└─ data/
   ├─ brand_metrics.parquet    브랜드별 지표 테이블 - B 담당
   ├─ sector_trend.parquet     업종별 신규 등록률·등록취소율 - A 담당
   ├─ sector_retention.parquet 업종별 등록 유지율 - A 담당
   ├─ sector_treemap.parquet   업종별 가맹점·브랜드 수 - A 담당
   ├─ region_sales.parquet     시도별 업종 면적당 매출 - A 담당
   └─ sido_geo.json            시도 경계 (지도용) - A 담당

```

## 2. 실행 방법 (Mac)

처음 한 번: 설치

```
cd franchise-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

실행 (매번)
압축을 푼 폴더 이름이 franchise-app이 아니면 cd 뒤에 실제 폴더 이름을 넣어 주세요.

```
cd franchise-app
source .venv/bin/activate
streamlit run 홈.py
```

- 반드시 터미널에서 `streamlit run 홈.py`로 실행합니다. VS Code의 ▷ 실행 버튼은 쓰지 않습니다.
- 코드를 수정한 뒤에는 브라우저에서 새로고침(Cmd+R)만 하면 됩니다.
- 안 열리면 터미널에 나온 Local URL을 크롬에 붙여넣습니다.
- 크롬 자동 번역이 켜져 있으면 한글이 이상하게 바뀌므로 꺼 주세요.

## 3. 상태(session_state) 키 규칙

화면 간 선택값은 `st.session_state`로 공유합니다. 키 이름은 `common/state.py`의 상수만 사용합니다.

| 상수 | 키 | 타입 | 기본값 | 설정하는 곳 | 사용하는 곳 |
|---|---|---|---|---|---|
| YEAR | year | int | 2025 | 사이드바 | 전 화면 |
| MIN_STORES | min_stores | int (5/10/20) | 10 | 사이드바 | 전 화면 |
| SECTOR | sector | str 또는 None | None | 화면1 트리맵 클릭 | 화면2 |
| BUDGET_RANGE | budget_range | (int, int), 천원 | (0, 500,000) | 화면2 | 화면2 |
| REGION | region | str 또는 None | None | 화면3 (참고용) | 화면3 |
| WEIGHTS | weights | dict (closure, growth, sales, multiple) | .30/.20/.20/.30 | 화면2 슬라이더 | 화면2, 3 |
| CANDIDATES | candidates | list[str] (브랜드 ID) | [] | 화면2 | 화면2, 3 |
| COMPARE_SET | compare_set | list[str], 최대 4개 | [] | 화면2 | 화면3 |
| HIDE_NEW | hide_new | bool | True | 화면2 토글 | 화면2 |

브랜드 ID는 `make_brand_id(corp_nm, brand_nm, mlsfc_nm)`가 만드는 `"법인명|브랜드명|업종중분류"` 문자열입니다.
창업비용 범위(단위: 천원). 상한 500,000은 "상한 없음"을 뜻합니다. 화면2의 슬라이더(만원 단위)가 바꿉니다.

### 규칙

1. 키는 문자열을 직접 쓰지 않고 상수로만 씁니다. (`st.session_state[YEAR]`, `st.session_state["year"]`는 사용하지 않습니다.)
2. 값을 바꾸는 코드는 위 표의 "설정하는 곳" 한 군데에만 둡니다. 다른 화면은 읽기만 합니다.
3. 모든 페이지 맨 위에서 `init_state()`를 호출합니다.
4. 위젯의 key에는 상태 키를 그대로 쓰지 않습니다. 위젯 key는 `_w_` 접두사를 붙이고, `on_change`로 상태 키에 복사합니다. (페이지를 옮기면 위젯 값이 사라지는 문제를 막기 위함입니다. `common/sidebar.py` 참고)
5. 모든 페이지는 `render_sidebar(df)`를 호출해 같은 사이드바를 보여 줍니다.
5-1. 모든 페이지 맨 아래에서 `render_footer()`를 호출해 데이터 해석 유의사항을 보여 줍니다. (`st.stop()` 앞에서도 호출)
6. 키를 추가하거나 바꿀 때는 이 표를 먼저 수정하고 팀에 알립니다.
7. 기준 연도는 2019~2025만 선택할 수 있습니다. (2017년은 전년도 값이 없고 2018년은 모든 브랜드가 '신규'로 판정되기 때문입니다.)

## 4. 페이지 템플릿

새 페이지는 아래 형태로 시작합니다.

```python
import streamlit as st
from common.state import init_state, YEAR, MIN_STORES
from common.data import load_data, get_scores
from common.sidebar import render_sidebar
from common.footer import render_footer

st.set_page_config(page_title="페이지 이름", layout="wide")
init_state()
df = load_data()
render_sidebar(df)

result = get_scores(st.session_state[YEAR], st.session_state[MIN_STORES])

# ... 화면 내용 ...

render_footer()   # 맨 아래
```

## 화면 간 연동
- 화면2(후보탐색): 표에서 행을 체크하고 '선택한 브랜드를 비교에 담기'를 누르면 compare_set에 담깁니다. (최대 4개, '비교 목록 비우기'로 초기화)
- 화면3(브랜드비교): compare_set을 읽기만 합니다. 담긴 브랜드가 없으면 안내 문구가 나옵니다.

### 화면2 지표 가중치 (후보탐색)

- 화면2의 '지표 가중치 조절'에서 폐점률·순성장률·가맹점 평균 매출·초기비용 대비 매출 배수의 가중치를 0~100(5 단위)으로 조절합니다. 기본값은 30/20/20/30입니다.
- 합계가 100이 아니어도 `compute_score`가 비율로 환산합니다. 모두 0이면 반영하지 않고 이전 값을 유지합니다.
- 값은 `WEIGHTS`에 저장되어 화면2의 순위표·차트와 화면3의 종합 점수에 같은 가중치가 적용됩니다. 위젯 key는 `_w_wt_closure`, `_w_wt_growth`, `_w_wt_sales`, `_w_wt_multiple`입니다.
- `get_scores(year, min_stores, weight_items)`의 `weight_items`에는 `tuple(sorted(weights.items()))`를 넘깁니다. (캐시 키로 쓰기 위해 tuple이어야 합니다.)

### 화면2 차트 탭 (후보탐색)

- 점수 안내 문구와 순위표 사이에 탭 2개가 있습니다. '브랜드 분포(버블)'는 `render_bubble(result)`, '업종별 분포(상자 그림)'는 `render_box(result)`를 호출합니다.
- 두 차트는 순위표와 같은 `result`(기준 연도, 최소 가맹점수, 업종, 창업비용 범위 적용)를 받습니다. '신규 브랜드 제외'는 표에만 적용되고 차트에는 영향이 없습니다.
- 버블 차트는 종합 점수를 산출한 브랜드만 표시합니다.

### 화면1 → 화면2 업종 연동

- `SECTOR`(업종 중분류 이름, 예: "치킨")는 **화면1(업종현황)의 트리맵 클릭으로만** 바꿉니다. 해제도 화면1의 "선택 해제" 버튼으로만 합니다.
- 화면2(후보탐색)는 `SECTOR`를 읽어서 `indutyMlsfcNm`이 같은 브랜드만 보여 줍니다. 값이 `None`이면 전체 업종입니다.
- 화면1의 지도는 `SECTOR`를 기준으로 그려지며, 면적당 매출 자료는 2022년부터 있어서 기준 연도가 2021년 이하면 안내문구가 나옵니다.

### 화면1 파일 (A 담당)

| 파일 | 내용 |
|---|---|
| `charts_sector.py` | 화면1 차트 함수 4개 (`render_sector_treemap`, `render_region_map`, `render_sector_trend`, `render_sector_retention`) |
| `data/sido_geo.json` | 시도 경계 (출처: southkorea/southkorea-maps, 통계청 2013 시도 단위 단순화 버전) |
| `pages/1_업종현황.py` | 화면1 본문 (위젯 key: `_w_treemap`, `_w_ret_group`) |

## 5. 데이터와 점수 (요약)

- `data/brand_metrics.parquet`: 2017~2025년, 브랜드·연도 단위 지표 테이블
- `get_scores(year, min_stores, weight_items=None)`: 선택한 연도와 최소 가맹점수, 가중치 기준으로 점수를 계산해 돌려줍니다. `weight_items`가 없으면 기본 가중치를 씁니다.
- 점수 산식, 지표 정의는 B가 작성한 지표 정의서를 따릅니다.
- 점수는 업종 중분류 내 백분위 가중합이며, 결측이 있는 브랜드는 "산출 불가"입니다.

### 화면1용 데이터 (A 담당)

`common/data.py`의 함수로 읽습니다. (캐시 사용)

| 함수 | 파일 | 내용 | 행 수 |
|---|---|---|---|
| load_sector_treemap() | data/sector_treemap.parquet | 업종 대분류→중분류별 브랜드 수·가맹점 수 (2017~2025) | 394 |
| load_sector_trend() | data/sector_trend.parquet | 업종 대분류별 신규 등록률·등록취소율 추이 | 27 |
| load_sector_retention() | data/sector_retention.parquet | 업종별·연차별 등록 유지율 (2021년 등록 브랜드 기준) | 45 |
| load_region_sales() | data/region_sales.parquet | 시도별 업종 면적당 매출 (2022~2025, 결측 있음) | 2,992 |

- 업종 중분류 이름은 brand_metrics와 동일합니다. 화면1에서 고른 업종은 `sector` 상태 키에 담고, 화면2가 이 값으로 필터합니다.
- `sector`를 바꾸는 곳은 화면1 한 곳뿐입니다.

### 차트 함수 (`charts.py`, C 담당)

| 함수 | 내용 |
|---|---|
| `render_bubble(df, score_col="score")` | 창업비용(x, 로그 눈금)·매출 배수(y)·가맹점수(크기)·종합 점수(색) 버블차트. 매출 배수는 0.17~23.16배 밖의 값을 잘라서 표시하고, 창업비용 축은 4,000~600,000천원 안으로 제한합니다. 축 범위는 표시된 브랜드 값에 맞춰 자동으로 정해집니다. 종합 점수를 산출한 브랜드만 표시합니다. |
| `render_box(df, top_n=12)` | 업종 중분류별 창업비용 박스플롯 (브랜드 수 상위 12개 업종) |

- 입력 `df`는 브랜드 표입니다. `render_bubble`은 `brandNm`, `indutyMlsfcNm`, `smtnAmt`, `sales_multiple`, `frcsCnt`, `score` 컬럼이 필요하고, `render_box`는 `brandNm`, `indutyMlsfcNm`, `smtnAmt` 컬럼이 필요합니다. 화면2에서 필터링한 `result`를 그대로 넘기면 됩니다.
- 금액 단위는 모두 **천원**입니다 (`smtnAmt` = 창업비용 합계). 매출 배수(`sales_multiple`)는 배 단위이며 투자회수기간이 아닙니다.
- 차트 함수는 C, 화면2 페이지 배치(탭, 안내 문구)도 반영을 마쳤습니다.

## 6. 담당 구분

| 역할 | 내용 |
|---|---|
| A 데이터 파이프라인 | `data/` 파일 생성·갱신 |
| B 지표·점수 | `metrics.py`, 지표 정의서 |
| C 앱 뼈대·통합 | `홈.py`, `pages/`, `common/`, `charts.py`, 배포 |
| D 브랜드 비교·문서 | 화면3, 발표·보고서 문서 |

## 7. 배포

Streamlit Community Cloud로 배포합니다. GitHub 저장소(`franchise-dashboard`)에 파일을 올리고 Main file path를 `홈.py`로 지정합니다. 패키지는 `requirements.txt`로 설치됩니다.

- 배포 주소: (배포 후 여기에 추가)
- 코드를 고치면 GitHub 저장소의 파일을 같은 이름으로 다시 올려 덮어씁니다. 잠시 뒤 배포 앱에도 반영됩니다.

## 알려진 한계 (팀 논의 결과)

1. **법인명이 바뀐 브랜드의 추이 그래프 (화면3)**: 점수와 신규 판정은 브랜드를 이어서 계산하지만, 화면3 추이 그래프는 `법인명|브랜드명|업종` 기준이라 법인명이 바뀐 브랜드(예: BHC)는 선이 바뀐 해 이후부터만 나옵니다. 지금은 이 방식을 유지하고 화면에 안내 문구를 둡니다. 선경님 일정이 되면 최종 발표 전까지 brand_metrics에 브랜드 연결 컬럼(lineage)을 추가하는 방식으로 바꿉니다.
2. **신규 브랜드 제외와 점수 (화면2)**: '신규 브랜드 제외'는 점수를 계산한 뒤 표에서만 거릅니다. 점수(백분위)에는 신규 브랜드가 포함됩니다. 2025년·최소 가맹점수 10 기준으로 신규를 빼고 백분위를 다시 계산해 본 결과 점수가 크게 달라지지 않아 지금 방식을 유지하고 한계 문구를 둡니다.
3. **지역 정보**: 원자료에 브랜드별 지역 정보가 없어서 지역으로 브랜드를 거르는 필터는 만들지 않습니다. 지역은 화면3의 '비교 지역 선택'에서 해당 지역·업종의 평균 면적당 매출(`region_sales`)을 기준선으로 보여주는 용도로만 씁니다. (2022년 이후 자료)
4. **버블 차트의 값 자르기 (화면2)**: 매출 배수가 0.17~23.16배 밖이거나 창업비용이 4,000~600,000천원 밖인 브랜드는 값을 잘라서 가장자리에 표시합니다. 매출 배수 축 구성은 선경님 확인 전입니다.
5. **직영점 정보**: 기획안의 업종 단위 직영점 안내는 앱에 넣지 않았습니다. 직영점포수 데이터(업종개황)를 수집하지 않아 앱 데이터에 없습니다.
