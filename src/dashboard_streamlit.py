
import streamlit as st
import json
import os
import pandas as pd
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="업비트 자동매매 대시보드", layout="wide")

# 1분(60,000ms)마다 자동 새로고침
st_autorefresh(interval=60 * 1000, key="datarefresh")

state_path = os.path.join(os.path.dirname(__file__), "coin_states.json")

st.title("업비트 자동매매 실시간 대시보드")

# 자동 새로고침(1분마다)
st_autorefresh = st.experimental_rerun if hasattr(st, "experimental_rerun") else lambda: None
st.button("새로고침", on_click=st_autorefresh)

def load_states():
    try:
        with open(state_path) as f:
            return json.load(f)
    except Exception:
        return {}

coin_states = load_states()

if not coin_states:
    st.warning("코인 상태 데이터가 없습니다.")
else:
    df = pd.DataFrame([
        {
            "코인": coin,
            "매수가": state.get("buy_price"),
            "보유수량": state.get("bought_volume"),
            "최근 매매시각": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(state.get("last_trade_time", 0))),
            "일일 매매횟수": state.get("trade_count_today"),
            "체결상태": state.get("order_status", "")
        }
        for coin, state in coin_states.items()
    ])
    st.dataframe(df, use_container_width=True)

    # 반응형: 모바일/PC 모두 보기 좋게 자동 조정됨

st.info("페이지 새로고침(↻) 또는 버튼 클릭으로 최신 상태를 확인하세요.")

st.sidebar.header("전략 파라미터 조정")
min_expected_profit = st.sidebar.slider("최소 기대수익률(%)", 0.0, 5.0, 0.3, 0.1)
max_trades_per_day = st.sidebar.number_input("1일 최대 매매 횟수", 1, 50, 10)
top_n = st.sidebar.number_input("포트폴리오 종목 수", 1, 20, 5)
if st.sidebar.button("적용"):
    with open("strategy_params.json", "w") as f:
        json.dump({
            "MIN_EXPECTED_PROFIT": min_expected_profit / 100,
            "MAX_TRADES_PER_DAY": int(max_trades_per_day),
            "TOP_N": int(top_n)
        }, f)
    st.success("전략 파라미터가 저장되었습니다.")

import pandas as pd
st.header("거래내역 및 수익률 분석")
if os.path.exists("trade_history.csv"):
    df = pd.read_csv("trade_history.csv")
    st.subheader("누적 거래내역 (실시간)")
    st.dataframe(df, use_container_width=True)

    # 누적 손익, 일별 손익, 종목별 누적 손익 등 다양한 누적 지표 시각화
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['profit'] = df.apply(lambda row: float(row['price']) * float(row['volume']) if row['type']=='sell' else -float(row['price']) * float(row['volume']), axis=1)

    # 누적 손익(전체)
    df['cum_profit'] = df['profit'].cumsum()
    st.line_chart(df.set_index('datetime')['cum_profit'], height=250)

    # 일별 손익
    daily = df.groupby(df['datetime'].dt.date)['profit'].sum()
    st.bar_chart(daily, height=200)

    # 종목별 누적 손익
    if 'market' in df.columns:
        coin_profit = df.groupby('market')['profit'].sum().sort_values(ascending=False)
        st.bar_chart(coin_profit, height=200)
else:
    st.info("거래내역이 없습니다.")