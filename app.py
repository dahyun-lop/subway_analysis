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

# --- 시나리오 1: 강수 등급별 지하철 이용 분석 ---
st.header("1. ☔ 강수 등급별 승/하차 이용 행태")

# 업로드하신 데이터 수치에 맞춰 단계를 최적화한 SQL
# 1단계: 2월(3.2), 2단계: 1월(7.6), 3단계: 4월(29.8), 4단계: 3월(43.9)
query1 = """
SELECT 
    CASE 
        WHEN B.강수량 < 5 THEN '1단계 (쾌적)'
        WHEN B.강수량 < 10 THEN '2단계 (약한비)'
        WHEN B.강수량 < 35 THEN '3단계 (보통비)'
        ELSE '4단계 (폭우)'
    END AS 강수등급,
    AVG(A.승차총승객수) AS 평균승차객수,
    AVG(A.하차총승객수) AS 평균하차객수
FROM 승하차 A
JOIN 강수량 B ON SUBSTR(A.사용일자, 1, 6) = B.년월
GROUP BY 강수등급
ORDER BY CASE 강수등급 
    WHEN '1단계 (쾌적)' THEN 1 
    WHEN '2단계 (약한비)' THEN 2 
    WHEN '3단계 (보통비)' THEN 3 
    WHEN '4단계 (폭우)' THEN 4 END
"""

try:
    df1 = pd.read_sql(query1, get_connection())

    # 레이아웃: 왼쪽(차트 2개), 오른쪽(SQL/인사이트)
    col1, col2 = st.columns([2.5, 1])

    with col1:
        # 서브플롯 생성
        fig = make_subplots(
            rows=1, cols=2, 
            subplot_titles=("<b>평균 승차객 수</b>", "<b>평균 하차객 수</b>"),
            horizontal_spacing=0.12
        )

        # 1. 평균 승차객 수 (진한 파란색)
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균승차객수'],
                marker_color='#074799', # 더 진한 신뢰감 있는 블루
                text=df1['평균승차객수'].apply(lambda x: f"{x:,.0f}"),
                textposition='outside',
                name="승차객"
            ), row=1, col=1
        )

        # 2. 평균 하차객 수 (밝은 파란색)
        fig.add_trace(
            go.Bar(
                x=df1['강수등급'], y=df1['평균하차객수'],
                marker_color='#40A2E3',
                text=df1['평균하차객수'].apply(lambda x: f"{x:,.0f}"),
                textposition='outside',
                name="하차객"
            ), row=1, col=2
        )

        # 차트 디테일 설정
        fig.update_layout(
            height=480,
            showlegend=False,
            margin=dict(t=60, b=40, l=20, r=20),
            plot_bgcolor='white',
            font=dict(size=12)
        )
        
        # Y축 격자선 추가
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', row=1, col=2)

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 사용된 SQL 섹션
        st.markdown("#### **사용된 SQL**")
        st.code(query1, language='sql')

        # 데이터 인사이트 섹션
        st.markdown("---")
        st.markdown("#### **💡 데이터 인사이트**")
        
        # 실제 데이터가 존재하는지 확인 후 인사이트 출력
        if not df1.empty:
            st.success(f"""
            * **최대 이용 구간:** '{df1.iloc[0]['강수등급']}'에서 가장 높은 이용량을 보입니다.
            * **강수량 영향:** 강수량이 {df1.iloc[-1]['강수등급']} 수준으로 높아질 때 승/하차 인원의 변화폭을 확인하세요.
            * **균형 분석:** 승차와 하차 패턴이 모든 강수 등급에서 유사하게 나타나는지 시각적으로 비교 가능합니다.
            """)
        else:
            st.warning("데이터 조인 결과가 없습니다. '승하차' 테이블에 2026년 1~4월 데이터가 있는지 확인해주세요.")

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")

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
