import requests
import datetime

UPBIT_API_URL = "https://api.upbit.com"

# 전체 KRW마켓 종목 조회
def get_krw_markets():
    url = f"{UPBIT_API_URL}/v1/market/all"
    res = requests.get(url, params={"isDetails": False})
    markets = res.json()
    return [m['market'] for m in markets if m['market'].startswith('KRW-')]

# 각 종목별 1개월 수익률 계산
def get_monthly_returns(markets):
    returns = []
    for market in markets:
        url = f"{UPBIT_API_URL}/v1/candles/days"
        params = {"market": market, "count": 30}
        res = requests.get(url, params=params)
        candles = res.json()
        if len(candles) < 30:
            continue
        price_30d_ago = candles[-1]['trade_price']
        price_now = candles[0]['trade_price']
        ret = (price_now - price_30d_ago) / price_30d_ago
        returns.append({"market": market, "return": ret})
    returns.sort(key=lambda x: x['return'], reverse=True)
    return returns

# 포트폴리오 선정 (상위 N개, 최소매매금액 5000원 이상 분배)
def select_portfolio(returns, total_balance, min_amount=5000, top_n=5):
    selected = returns[:top_n]
    n = len(selected)
    amount_per_coin = max(min_amount, total_balance // n)
    portfolio = []
    for coin in selected:
        portfolio.append({
            "market": coin['market'],
            "amount": amount_per_coin
        })
    return portfolio

if __name__ == "__main__":
    markets = get_krw_markets()
    returns = get_monthly_returns(markets)
    portfolio = select_portfolio(returns, 1000000)
    print(portfolio)
