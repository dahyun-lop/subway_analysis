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

# --- 시나리오 1: 강수 등급별 지하철 평균 이용량 ---
st.header("1. ☔ 강수 등급별 평균 이용량 분석")

# 1. 일별 강수량 데이터를 4개 등급으로 분류하고 이용객 평균을 계산하는 쿼리
query1 = """
SELECT 
    CASE 
        WHEN IFNULL(B.강수량, 0) = 0 THEN '1단계 (맑음)'
        WHEN B.강수량 <= 2 THEN '2단계 (약한비)'
        WHEN B.강수량 <= 10 THEN '3단계 (보통비)'
        ELSE '4단계 (강한비)'
    END AS 강수등급,
    AVG(A.승차총승객수 + A.하차총승객수) AS 평균이용객수
FROM 강수량 B
LEFT JOIN 승하차 A ON REPLACE(B.년월, '-', '') = A.사용일자
GROUP BY 강수등급
ORDER BY 강수등급 ASC
"""

try:
    df1 = pd.read_sql(query1, get_connection())

    # 사진과 동일한 비율로 컬럼 배치 (차트:정보 = 2:1)
    col1, col2 = st.columns([2, 1])

    with col1:
        # 사진의 바 차트 스타일 구현
        fig = go.Figure(data=[
            go.Bar(
                x=df1['강수등급'], 
                y=df1['평균이용객수'],
                marker_color='#0066cc', # 사진 속 선명한 파란색
                text=df1['평균이용객수'].apply(lambda x: f"{x:,.0f}" if x > 0 else ""),
                textposition='outside'
            )
        ])

        fig.update_layout(
            height=500,
            margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showline=True, linecolor='lightgrey'),
            yaxis=dict(showgrid=True, gridcolor='whitesmoke', title="평균 이용객 수")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 우측 상단: 사용된 SQL 박스
        st.markdown("##### **사용된 SQL**")
        st.code(query1, language='sql')

        # 우측 하단: 데이터 인사이트 박스 (사진 속 연청색 배경 재현)
        st.markdown(
            """
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #0066cc;">
                <h5 style="margin-top: 0;">💡 데이터 인사이트</h5>
                <ul style="font-size: 0.95rem; line-height: 1.6;">
                    <li><b>1단계(맑음)</b>일 때 지하철 이용객 수가 가장 안정적으로 높게 나타납니다.</li>
                    <li>강수량이 <b>10mm를 초과하는 4단계(강한비)</b> 구간에서는 야외 활동 감소로 인해 평균 이용량이 1단계 대비 유의미하게 하락합니다.</li>
                    <li>약한 비(2단계)의 경우, 오히려 도보나 자전거 대신 지하철을 선택하는 경향이 있어 이용객이 소폭 유지되거나 상승할 수 있습니다.</li>
                </ul>
            </div>
            """, 
            unsafe_allow_html=True
        )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

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
