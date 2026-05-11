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

# --- 시나리오 1: 강수 등급별 이용 분석 (에러 수정본) ---
st.header("1. ☔ 강수 등급별 승/하차 이용 행태")

# 기존에 확인된 컬럼(승차총승객수, 하차총승객수)만 사용합니다.
query1 = """
SELECT 
    CASE 
        WHEN B.강수량 < 5 THEN '1단계 (맑음/약한비)'
        WHEN B.강수량 < 15 THEN '2단계 (보통)'
        WHEN B.강수량 < 30 THEN '3단계 (강한비)'
        ELSE '4단계 (매우강한비/폭우)'
    END AS 강수등급,
    AVG(A.승차총승객수) AS 평균승차객수,
    AVG(A.하차총승객수) AS 평균하차객수
FROM 승하차 A
JOIN 강수량 B ON SUBSTR(A.사용일자, 1, 6) = B.년월
GROUP BY 강수등급
ORDER BY B.강수량 ASC
"""

try:
    df1 = pd.read_sql(query1, get_connection())

    col1, col2 = st.columns([2.5, 1])

    with col1:
        fig = make_subplots(
            rows=1, cols=2, 
            subplot_titles=("<b>평균 승차객 수</b>", "<b>평균 하차객 수</b>"),
            horizontal_spacing=0.15
        )

        # 1. 평균 승차객 수
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균승차객수'],
                marker_color='#004AAD',
                text=df1['평균승차객수'].map('{:,.0f}'.format),
                textposition='outside',
                name="승차객"
            ), row=1, col=1
        )

        # 2. 평균 하차객 수
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균하차객수'],
                marker_color='#33A1FF', # 조금 더 밝은 파란색
                text=df1['평균하차객수'].map('{:,.0f}'.format),
                textposition='outside',
                name="하차객"
            ), row=1, col=2
        )

        fig.update_layout(height=450, showlegend=False, margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📝 사용된 SQL")
        st.code(query1, language='sql')
        st.markdown("### 💡 인사이트")
        st.info("강수 등급이 높아질수록 승차와 하차 인원 모두 감소하는지 확인해보세요.")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.write("팁: 테이블에 '승차총승객수'와 '하차총승객수' 컬럼이 있는지 확인해주세요.")

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
