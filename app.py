import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# 페이지 설정
st.set_page_config(page_title="서울 지하철 데이터 분석", layout="wide")

# DB 파일 경로 확인
DB_PATH = 'subway.db'

if not os.path.exists(DB_PATH):
    st.error(f"⚠️ '{DB_PATH}' 파일을 찾을 수 없습니다. 데이터베이스 파일이 같은 폴더에 있는지 확인해주세요!")
    st.stop()

# DB 연결 함수
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

st.title("🚇 서울 지하철 데이터 분석 대시보드")
st.markdown("승하차 데이터, 무임승차 현황, 기상 정보를 통합 분석합니다.")

# --- 시나리오 1: 비와 지하철 이용의 상관관계 ---
st.header("1. ☔ 비와 지하철 이용의 상관관계")

# 수정된 쿼리: 각 테이블을 먼저 그룹화한 후 JOIN 하여 데이터 뻥튀기 방지
query1 = """
SELECT 
    A.년월, 
    A.총이용객, 
    B.평균강수량
FROM (
    SELECT SUBSTR(사용일자, 1, 6) AS 년월, 
           SUM(승차총승객수 + 하차총승객수) AS 총이용객
    FROM 승하차 
    GROUP BY SUBSTR(사용일자, 1, 6)
) A
JOIN (
    SELECT 년월, 
           AVG(강수량) AS 평균강수량
    FROM 강수량 
    GROUP BY 년월
) B ON A.년월 = B.년월
ORDER BY A.년월
"""

df1 = pd.read_sql(query1, get_connection())

# [핵심 수정] X축 데이터 타입을 문자열로 변환 (202603 -> "2026-03" 형태 권장)
df1['년월'] = df1['년월'].astype(str) 

fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# 막대 차트 (총 이용객 수)
fig1.add_trace(
    go.Bar(
        x=df1['년월'], 
        y=df1['총이용객'], 
        name="총 이용객 수", 
        marker_color='lightblue',
        opacity=0.7
    ), 
    secondary_y=False
)

# 라인 차트 (평균 강수량) - mode='lines+markers' 추가하여 단일 데이터도 보이게 설정
fig1.add_trace(
    go.Scatter(
        x=df1['년월'], 
        y=df1['평균강수량'], 
        name="평균 강수량(mm)", 
        mode='lines+markers+text', # 선과 점을 모두 표시
        line=dict(color="royalblue", width=3),
        marker=dict(size=8)
    ), 
    secondary_y=True
)

# 레이아웃 업데이트
fig1.update_layout(
    title_text="월별 이용객 수와 강수량 비교 (이중축)",
    xaxis_type='category', # X축을 범주형으로 명시적 지정
    hovermode="x unified"
)

fig1.update_yaxes(title_text="<b>이용객 수</b>", secondary_y=False)
fig1.update_yaxes(title_text="<b>강수량 (mm)</b>", secondary_y=True)

st.plotly_chart(fig1, use_container_width=True)

with st.expander("💡 인사이트 보기"):
    st.write("강수량이 높은 달(장마철 등)의 이용객 변화를 통해 날씨가 지하철 이용에 미치는 영향을 파악할 수 있습니다.")

# --- 시나리오 2: 실버 노선 분석 ---
st.header("2. 👴 실버 노선 분석 (무임승차 비중 TOP 10)")
query2 = """
SELECT A.역명, A.노선명,
       CAST(SUM(B.총승차) AS FLOAT) / SUM(A.승차총승객수) * 100 AS 무임승차비중
FROM 승하차 A
JOIN 무임승하차 B ON A.역명 = B.역 AND A.노선명 = B.호선
GROUP BY A.역명, A.노선명
ORDER BY 무임승차비중 DESC LIMIT 10
"""
df2 = pd.read_sql(query2, get_connection())

fig2 = px.bar(df2, x='무임승차비중', y='역명', color='노선명', orientation='h',
             title="전체 승객 대비 무임승차 비중이 가장 높은 역",
             labels={'무임승차비중': '무임승차 비중 (%)'},
             color_discrete_sequence=px.colors.qualitative.Pastel)
fig2.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig2, use_container_width=True)

with st.expander("💡 인사이트 보기"):
    st.write("무임승차 비중이 높은 역들은 주로 노인 인구 밀집 지역이나 전통시장, 대형 공원 인근역일 가능성이 높습니다.")


# --- 시나리오 3: 호선별 출퇴근 패턴 (순유입 분석) ---
st.header("3. 🔄 호선별 순유입(승차-하차) 분석")
query3 = """
SELECT 노선명, 
       SUM(승차총승객수) - SUM(하차총승객수) AS 순유입
FROM 승하차
GROUP BY 노선명
ORDER BY 순유입 DESC
"""
df3 = pd.read_sql(query3, get_connection())

fig3 = px.bar(df3, x='노선명', y='순유입', color='순유입',
             title="호선별 순유입 총합 (승차 - 하차)",
             color_continuous_scale='RdBu_r')
st.plotly_chart(fig3, use_container_width=True)

with st.expander("💡 인사이트 보기"):
    st.write("순유입이 양수(+)인 노선은 주거지 중심(출근 시 승차 많음), 음수(-)인 노선은 업무지구 중심(출근 시 하차 많음)의 특성을 보입니다.")
