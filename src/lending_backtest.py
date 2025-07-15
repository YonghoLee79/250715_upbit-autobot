import pandas as pd
import numpy as np
from datetime import timedelta

# 샘플 거래내역 데이터 (실제는 trade_history.csv 사용)
df = pd.read_csv("trade_history.csv")

# 렌딩 이자율(연 5% 가정, 일 단위 환산)
LENDING_RATE = 0.05 / 365
LENDING_DAYS = 7  # 렌딩 기간(일)

# 전략 시뮬레이션 결과 저장
results = []

# 코인별로 매수-매도 쌍 찾기
for market in df['market'].unique():
    coin_df = df[df['market'] == market].sort_values('datetime')
    buys = coin_df[coin_df['type'] == 'buy']
    sells = coin_df[coin_df['type'] == 'sell']
    for idx, buy in buys.iterrows():
        # 렌딩 만기일 계산
        buy_time = pd.to_datetime(buy['datetime'])
        lend_end = buy_time + timedelta(days=LENDING_DAYS)
        # 해당 매수 이후 첫 매도 찾기
        sell = sells[sells['datetime'] > buy['datetime']].head(1)
        if not sell.empty:
            sell = sell.iloc[0]
            sell_time = pd.to_datetime(sell['datetime'])
            # 실제 보유기간(렌딩기간과 매도시점 중 짧은 쪽)
            hold_days = min((sell_time - buy_time).days, LENDING_DAYS)
            # 렌딩 이자 계산
            lending_profit = float(buy['amount']) * LENDING_RATE * hold_days
            # 시세차익 계산
            price_profit = (float(sell['price']) - float(buy['price'])) * float(buy['volume'])
            total_profit = price_profit + lending_profit
            results.append({
                'market': market,
                'buy_time': buy['datetime'],
                'sell_time': sell['datetime'],
                'hold_days': hold_days,
                'price_profit': price_profit,
                'lending_profit': lending_profit,
                'total_profit': total_profit
            })

# 결과 DataFrame
result_df = pd.DataFrame(results)
print("\n[코인빌리기 전략 시뮬레이션 결과]")
print(result_df)
print("\n총 수익(시세차익+이자):", result_df['total_profit'].sum())

# 누적 수익 그래프 (옵션)
try:
    import matplotlib.pyplot as plt
    result_df['cum_profit'] = result_df['total_profit'].cumsum()
    result_df['sell_time'] = pd.to_datetime(result_df['sell_time'])
    plt.plot(result_df['sell_time'], result_df['cum_profit'])
    plt.title('누적 수익(코인빌리기 전략)')
    plt.xlabel('날짜')
    plt.ylabel('누적 수익')
    plt.show()
except ImportError:
    pass

# 사용법 안내
print("\n[사용법]")
print("1. trade_history.csv에 거래내역을 기록하세요.")
print("2. lending_backtest.py를 실행하면 코인빌리기 전략의 누적 수익을 시뮬레이션합니다.")
print("3. 실제 자동매매에 적용하려면, 매수 후 업비트 렌딩 API(또는 수동 신청)를 호출하면 됩니다.")
