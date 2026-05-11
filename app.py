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

# --- 시나리오 1: 일일 강수 등급별 지하철 이용 행태 ---
st.header("1. ☔ 강수 등급별 승/하차 이용 행태 (일간 데이터 기준)")

# 1. 일자별 조인을 위해 날짜 형식을 맞추고(REPLACE), 강수량 수치에 따라 4단계로 분류
# 2. 업로드된 데이터의 분포(0~15.5mm)를 고려하여 임계값 조정
query1 = """
SELECT 
    CASE 
        WHEN IFNULL(B.강수량, 0) = 0 THEN '1단계 (맑음)'
        WHEN B.강수량 <= 2 THEN '2단계 (약한비)'
        WHEN B.강수량 <= 10 THEN '3단계 (보통비)'
        ELSE '4단계 (강한비)'
    END AS 강수등급,
    AVG(A.승차총승객수) AS 평균승차객수,
    AVG(A.하차총승객수) AS 평균하차객수
FROM 강수량 B
LEFT JOIN 승하차 A ON REPLACE(B.년월, '-', '') = A.사용일자
GROUP BY 강수등급
ORDER BY 강수등급 ASC
"""

try:
    df1 = pd.read_sql(query1, get_connection())

    # 레이아웃 구성
    col1, col2 = st.columns([2.5, 1])

    with col1:
        fig = make_subplots(
            rows=1, cols=2, 
            subplot_titles=("<b>평균 승차객 수</b>", "<b>평균 하차객 수</b>"),
            horizontal_spacing=0.12
        )

        # 1. 평균 승차객 수 (진한 파란색)
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균승차객수'],
                marker_color='#074799',
                text=df1['평균승차객수'].apply(lambda x: f"{x:,.0f}" if x > 0 else "데이터 없음"),
                textposition='outside',
                name="승차객"
            ), row=1, col=1
        )

        # 2. 평균 하차객 수 (밝은 파란색)
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균하차객수'],
                marker_color='#40A2E3',
                text=df1['평균하차객수'].apply(lambda x: f"{x:,.0f}" if x > 0 else "데이터 없음"),
                textposition='outside',
                name="하차객"
            ), row=1, col=2
        )

        fig.update_layout(
            height=500,
            showlegend=False,
            margin=dict(t=60, b=40, l=20, r=20),
            plot_bgcolor='white'
        )
        
        # Y축 격자선 및 범위 최적화
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', row=1, col=2)

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### **업데이트 사항**")
        st.info("기존 월별 분석에서 **일별 분석**으로 전환하여 1~4단계를 모두 구현했습니다.")
        
        st.markdown("#### **사용된 SQL**")
        st.code(query1, language='sql')
        
        st.markdown("#### **💡 분석 포인트**")
        st.success("""
        * 일별 강수량이 0인 날과 비가 온 날의 이용객 차이를 극명하게 비교할 수 있습니다.
        * **1단계(맑음)** 대비 **4단계(강한비)**의 이용객 감소폭을 통해 날씨 민감도를 파악해 보세요.
        """)

except Exception as e:
    st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")

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
