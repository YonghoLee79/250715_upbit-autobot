import os
from dotenv import load_dotenv
from backtest.data_loader import DataLoader
from backtest.simulator import BacktestSimulator
from backtest.report import BacktestReport
from auto_optimizer import auto_optimize
from ai_verifier import AIVerifier
from telegram_alert import TelegramAlert
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def example_strategy(date, positions, balance, data_dict, params):
    N = params.get('top_n', 3)
    returns = []
    for market, df in data_dict.items():
        if date not in df.index or len(df.loc[:date]) < 30:
            continue
        price_now = df.loc[date]['close']
        price_30d_ago = df.loc[:date].iloc[-30]['close']
        ret = (price_now - price_30d_ago) / price_30d_ago
        returns.append((market, ret))
    returns.sort(key=lambda x: x[1], reverse=True)
    top = returns[:N]
    invest_per_coin = balance // len(top) if top else 0
    result = {}
    for market, _ in top:
        price = data_dict[market].loc[date]['close']
        amount = int(invest_per_coin // price)
        if amount * price >= 5000:
            result[market] = amount
    return result

def main():
    load_dotenv()
    start = '2023-01-01'
    end = '2025-07-01'
    markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA']
    loader = DataLoader()
    data_dict = {m: loader.get_ohlcv(m, start, end) for m in markets}
    rebalance_dates = data_dict[markets[0]].index.tolist()

    # 1. 전략 파라미터 자동 최적화
    param_grid = [
        {'rebalance_period': 7, 'max_coin_ratio': 0.2, 'top_n': 3},
        {'rebalance_period': 14, 'max_coin_ratio': 0.2, 'top_n': 3},
        {'rebalance_period': 30, 'max_coin_ratio': 0.2, 'top_n': 3},
        {'rebalance_period': 30, 'max_coin_ratio': 0.3, 'top_n': 5},
    ]
    best_param, best_history = auto_optimize(example_strategy, data_dict, rebalance_dates, param_grid)

    # 2. AI 기반 전략 추천
    ai = AIVerifier(openai_api_key=os.getenv("OPENAI_API_KEY"))
    prompt = "최근 3개월 비트코인, 이더리움, 리플의 가격 변동과 시장 상황을 요약하고, 자동매매 전략을 추천해줘."
    is_positive, answer = ai.llm_check(prompt)
    print(f"AI 전략 추천: {answer}")

    # 3. 성과 리포트 및 그래프
    report = BacktestReport(best_history)
    summary_text = report.summary()
    report.plot()

    # 4. 텔레그램 알림 전송
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if telegram_token and telegram_chat_id:
        tg = TelegramAlert(telegram_token, telegram_chat_id)
        tg.send(f"[백테스트 결과]\n최적 파라미터: {best_param}\n누적 수익률: {summary_text}\nAI 전략 추천: {answer}")

if __name__ == '__main__':
    main()
