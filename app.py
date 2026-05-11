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

# --- 시나리오 1: 강수량별 지하철 평균 이용량 ---
st.header("1. ☔ 강수량별 지하철 평균 이용량")

# 강수량을 5mm 단위로 구간화(Binning)하여 평균 이용객 수 계산
query1 = """
SELECT 
    (CAST(B.강수량 / 5 AS INTEGER) * 5) AS 강수구간, 
    AVG(A.승차총승객수 + A.하차총승객수) AS 평균이용객수
FROM 승하차 A
JOIN 강수량 B ON SUBSTR(A.사용일자, 1, 6) = B.년월
GROUP BY 강수구간
ORDER BY 강수구간
"""

df1 = pd.read_sql(query1, get_connection())

# 2열 레이아웃 설정 (차트 비중을 더 크게)
col1, col2 = st.columns([2, 1])

with col1:
    # 막대 차트 생성
    fig1 = go.Figure(data=[
        go.Bar(
            x=df1['강수구간'].apply(lambda x: f"{x}mm ~ {x+4}mm"), 
            y=df1['평균이용객수'],
            marker_color='#0066cc' # 사진과 유사한 진한 파란색
        )
    ])

    fig1.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=450,
        xaxis_tickangle=0,
        plot_bgcolor='white'
    )
    
    fig1.update_yaxes(showgrid=True, gridcolor='lightgrey')
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # 우측 상단: 사용된 SQL
    st.info("**사용된 SQL**")
    st.code(query1, language='sql')

    # 우측 하단: 데이터 인사이트
    st.success("**💡 데이터 인사이트**")
    st.markdown("""
    * **적은 강수량(0~5mm)** 구간에서 지하철 이용객 수가 가장 높게 나타나는 경향이 있습니다.
    * **폭우가 내리는 구간**으로 갈수록 평균 이용객 수가 감소하며, 이는 야외 활동 위축이 지하철 이용량에도 영향을 미침을 시사합니다.
    """)

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
