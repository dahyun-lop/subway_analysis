import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# 0. 페이지 설정
st.set_page_config(page_title="지하철 데이터 분석 대시보드", layout="wide")

# 1. 데이터베이스 연결 및 에러 처리
db_path = '지하철분석.db'

if not os.path.exists(db_path):
    st.error("⚠️ 데이터베이스 파일이 없습니다. 경로를 확인해주세요!")
    st.stop()  # 파일이 없으면 여기서 실행 중단

def run_query(q):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(q, conn)

st.title("🚇 서울시 지하철 공공데이터 분석 대시보드")
st.markdown("지하철 이용 패턴과 날씨, 무임승차 현황을 한눈에 확인하세요.")

# --- 차트 1: 날씨별 이용객 변화 ---
st.header("1. ☔ 날씨별 이용객 변화 분석")
sql1 = """
SELECT 
    SUBSTR(A.사용일자, 1, 6) AS 년월,
    SUM(A.승차총승객수 + A.하차총승객수) AS 총이용객,
    AVG(B.강수량) AS 평균강수량
FROM 승하차 A
JOIN 강수량 B ON SUBSTR(A.사용일자, 1, 6) = B.년월
GROUP BY 년월
ORDER BY 년월
"""
df1 = run_query(sql1)

# 시각화 (라인 & 막대 혼합)
fig1 = go.Figure()
fig1.add_trace(go.Bar(x=df1['년월'], y=df1['총이용객'], name='총 이용객수', marker_color='skyblue'))
fig1.add_trace(go.Scatter(x=df1['년월'], y=df1['평균강수량'], name='평균 강수량(mm)', yaxis='y2', line=dict(color='red', width=3)))

fig1.update_layout(
    title='월별 지하철 이용객 및 강수량 추이',
    yaxis=dict(title='이용객 수'),
    yaxis2=dict(title='강수량(mm)', overlaying='y', side='right'),
    legend=dict(x=1.1, y=1)
)
st.plotly_chart(fig1, use_container_width=True)

with st.expander("🔍 SQL 쿼리 및 인사이트 보기"):
    st.code(sql1, language='sql')
    st.write("인사이트:")
    st.write("1. 강수량이 급증하는 여름철(장마기)에는 야외 활동이 줄어들어 전체 이용객 수가 소폭 감소하는 경향이 보입니다.")
    st.write("2. 비가 많이 오는 달과 적게 오는 달의 이용객 편차를 통해 기후가 대중교통 수요에 미치는 영향을 파악할 수 있습니다.")


# --- 차트 2: 역별 무임승차 비중 TOP 10 ---
st.header("2. 👴 역별 무임승차 비중 TOP 10")
sql2 = """
SELECT 
    A.역명, 
    A.노선명,
    SUM(B.총승차) AS 무임승차합계,
    SUM(A.승차총승객수) AS 총승차합계,
    (CAST(SUM(B.총승차) AS FLOAT) / SUM(A.승차총승객수)) * 100 AS 무임비중
FROM 승하차 A
JOIN 무임승하차 B ON A.역명 = B.역 AND A.노선명 = B.호선
GROUP BY A.역명, A.노선명
ORDER BY 무임비중 DESC
LIMIT 10
"""
df2 = run_query(sql2)

# 시각화 (가로 막대 차트)
fig2 = px.bar(df2, x='무임비중', y='역명', color='노선명', orientation='h',
             title="전체 승차객 대비 무임승차 비중 상위 10개 역",
             labels={'무임비중': '무임승차 비중 (%)'},
             text_auto='.1f')
fig2.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig2, use_container_width=True)

with st.expander("🔍 SQL 쿼리 및 인사이트 보기"):
    st.code(sql2, language='sql')
    st.write("인사이트:")
    st.write("1. 무임승차 비중이 높은 역들은 주로 종로3가, 제기동 등 전통시장이나 노인 복지 시설이 밀집한 지역임을 알 수 있습니다.")
    st.write("2. 특정 노선(1호선 등)에서 무임승차 비중이 두드러지게 나타나며, 이는 해당 지역의 인구 통계적 특성을 반영합니다.")


# --- 차트 3: 노선별 승하차 불균형(순유입) 분석 ---
st.header("3. 🔄 노선별 승하차 불균형 분석")
sql3 = """
SELECT 
    노선명, 
    SUM(승차총승객수) AS 총승차, 
    SUM(하차총승객수) AS 총하차,
    SUM(승차총승객수) - SUM(하차총승객수) AS 순유입
FROM 승하차
GROUP BY 노선명
"""
df3 = run_query(sql3)
df3['불균형절대값'] = df3['순유입'].abs()

# 시각화 (도넛 차트)
fig3 = px.pie(df3, values='불균형절대값', names='노선명', hole=0.4,
             title="노선별 승하차 불균형 정도 (승차-하차 절대값 기준)")
st.plotly_chart(fig3, use_container_width=True)

with st.expander("🔍 SQL 쿼리 및 인사이트 보기"):
    st.code(sql3, language='sql')
    st.write("인사이트:")
    st.write("1. 순유입(승차-하차) 값이 큰 노선은 주로 주거 밀집 지역을 통과하여 아침에 출근객이 많이 타는 노선입니다.")
    st.write("2. 반대로 순유출이 큰 노선은 대표적인 업무 지구(강남, 여의도 등)를 포함하고 있어 퇴근 시간에 하차 인원이 몰리는 특성을 보입니다.")