import os
from dotenv import load_dotenv
from upbit_api import UpbitAPI
from strategy import simple_monthly_target_strategy
from portfolio import get_krw_markets, get_monthly_returns, select_portfolio
import statistics

# 환경변수 로드
load_dotenv()

UPBIT_ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY')
UPBIT_SECRET_KEY = os.getenv('UPBIT_SECRET_KEY')
UPBIT_MARKET = os.getenv('UPBIT_MARKET', 'KRW-BTC')
START_BALANCE = 100000

# 수수료 설정 (업비트 기준)
TRADING_FEE = 0.0005  # 0.05%
EXCHANGE_FEE = 0.001  # 예시 환전 수수료 0.1%

def simple_monthly_target_strategy(balance, ticker, trading_fee, exchange_fee):
    """
    월 10% 수익률을 목표로 하는 단순 전략 예시.
    - 목표가 도달 시 익절, 손실폭 제한
    - 실제 매매에서는 더 정교한 전략 필요
    """
    current_price = float(ticker['trade_price'])
    fee = balance * (trading_fee + exchange_fee)
    action = None
    amount = 0.0
    # 목표가 도달하면 매도, 일정 손실이면 매수 (예시)
    if current_price > float(ticker['opening_price']) * 1.10:
        action = 'sell'
        amount = balance / current_price
    elif current_price < float(ticker['opening_price']) * 0.97:
        action = 'buy'
        amount = (balance - fee) / current_price
    return {'action': action, 'amount': amount}


import math
import datetime
import requests
import time
from telegram_alert import TelegramAlert

def main():
    print(f"업비트 자동매매 오토봇 시작: {UPBIT_MARKET}")
    if not UPBIT_ACCESS_KEY or not UPBIT_SECRET_KEY:
        raise ValueError("UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY를 .env에 설정하세요.")
    api = UpbitAPI(str(UPBIT_ACCESS_KEY), str(UPBIT_SECRET_KEY))
    # 텔레그램 알림 설정 (환경변수 또는 직접 입력)
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    tg = None
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        tg = TelegramAlert(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    while True:
        # 업비트 전체 자산(원화+코인) 평가금액 계산
        balances = api.get_balance()
        total_krw = 0.0
        tickers = []
        for b in balances:
            if b['currency'] == 'KRW':
                total_krw += float(b['balance'])
            elif float(b['balance']) > 0:
                tickers.append(f"KRW-{b['currency']}")
        # 코인 평가금액 합산
        if tickers:
            prices = api.get_ticker(",".join(tickers))
            if isinstance(prices, dict):
                prices = [prices]
            for b, t in zip(balances, prices):
                if b['currency'] == t['market'].split('-')[1]:
                    total_krw += float(b['balance']) * float(t['trade_price'])
        msg = f"[업비트 오토봇] 전체 평가금액(원화+코인): {total_krw:.2f} KRW"
        print(msg)
        if tg:
            tg.send(msg)
        if total_krw < 5000:
            print("매수 가능한 평가금액이 부족합니다.")
            time.sleep(60)
            continue

        # 여기에 선언!
        max_per_coin = total_krw * 0.2

        # 기준자산을 매번 현재 자산으로 갱신
        main.initial_krw = total_krw

        loss_rate = (total_krw - main.initial_krw) / main.initial_krw
        msg = f"누적 수익률: {loss_rate*100:.2f}% (기준자산: {main.initial_krw:.2f} KRW)"
        print(msg)
        if tg:
            tg.send(msg)
        if loss_rate < -0.10:
            msg = "누적 손실 -10% 초과! 전체 자산 현금화(매도) 실행"
            print(msg)
            if tg:
                tg.send(msg)
            # 전체 코인 시장가 매도
            for b in balances:
                if b['currency'] != 'KRW' and float(b['balance']) > 0:
                    market = f"KRW-{b['currency']}"
                    msg = f"시장가 전량매도: {market} {b['balance']}개"
                    print(msg)
                    if tg:
                        tg.send(msg)
                    sell_result = api.sell_market_order(market, float(b['balance']))
                    msg = f"매도 결과: {sell_result}"
                    print(msg)
                    if tg:
                        tg.send(msg)
            msg = "10분 후 재시작"
            print(msg)
            if tg:
                tg.send(msg)
            time.sleep(600)
            continue
        # 포트폴리오 자동 선정 (시장 상황 필터, 변동성/거래량/시총 고려, 기술적지표, 리밸런싱, 코인빌려주기)
        print("KRW마켓 전체 종목 조회 중...")
        markets = get_krw_markets()
        print(f"종목 수: {len(markets)}개, 수익률/변동성/거래량/시장상황 계산 중...")
        returns = []
        rsi_targets = []
        for market in markets:
            # 30일 캔들 조회
            url = f"https://api.upbit.com/v1/candles/days"
            params = {"market": market, "count": 30}
            res = requests.get(url, params=params)
            candles = res.json()
            if len(candles) < 30:
                continue
            price_30d_ago = candles[-1]['trade_price']
            price_now = candles[0]['trade_price']
            ret = (price_now - price_30d_ago) / price_30d_ago
            # 변동성(표준편차), 거래량평균
            prices = [c['trade_price'] for c in candles]
            vols = [c['candle_acc_trade_price'] for c in candles]
            volatility = statistics.stdev(prices)
            avg_vol = statistics.mean(vols)
            # RSI(14) 계산
            deltas = [prices[i] - prices[i+1] for i in range(len(prices)-1)]
            gains = [d for d in deltas if d > 0]
            losses = [-d for d in deltas if d < 0]
            avg_gain = sum(gains)/14 if len(gains)>=14 else 0.0001
            avg_loss = sum(losses)/14 if len(losses)>=14 else 0.0001
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            # 하락장 반등 신호: RSI 30 이하 종목만 별도 추림
            if rsi < 30:
                rsi_targets.append({"market": market, "rsi": rsi, "ret": ret, "vol": avg_vol})
            returns.append({
                "market": market,
                "return": ret,
                "volatility": volatility,
                "avg_vol": avg_vol,
                "rsi": rsi
            })
        # 전체 시장 평균 수익률로 하락장 필터링
        market_avg = statistics.mean([r['return'] for r in returns])
        if market_avg < -0.05:
            print("시장 전체가 하락장입니다. 현금 비중을 80%로 유지하고, RSI 30 이하 반등 신호 종목만 소액 매수/코인빌려주기 실행")
            # 현금 80% 유지, 20%만 rsi_targets에 분산
            invest_amount = total_krw * 0.2
            if rsi_targets:
                amount_per_coin = max(5000, min(invest_amount // len(rsi_targets), max_per_coin))
                for t in rsi_targets:
                    msg = f"[반등신호] {t['market']} : {amount_per_coin} KRW 매수 시도 및 코인빌려주기(렌딩) 실행"
                    print(msg)
                    if tg:
                        tg.send(msg)
                    buy_result = api.buy_market_order(t['market'], amount_per_coin)
                    msg = f"실제 매수 결과: {buy_result}"
                    print(msg)
                    if tg:
                        tg.send(msg)
                    # 코인빌려주기(렌딩) API 호출 예시 (실제 구현 필요)
                    # api.lending_coin(t['market'], amount_per_coin)
            else:
                print("RSI 30 이하 반등 신호 종목 없음. 현금 대기.")
        else:
            print("시장 정상. 분산 포트폴리오 매수.")
            # 변동성/거래량/수익률 조합으로 점수화(예시)
            for r in returns:
                r['score'] = r['return'] * 0.7 + (r['avg_vol']/1e9) * 0.2 - (r['volatility']/r['return'] if r['return']!=0 else 0) * 0.1
            returns.sort(key=lambda x: x['score'], reverse=True)
            portfolio = select_portfolio(returns, total_krw, min_amount=5000, top_n=5)
            print("추천 포트폴리오:")
            for p in portfolio:
                amount = min(p['amount'], max_per_coin)
                msg = f"{p['market']} : {amount} KRW (최대비중 적용)"
                print(msg)
                if tg:
                    tg.send(msg)
                buy_result = api.buy_market_order(p['market'], amount)
                msg = f"실제 매수 결과: {buy_result}"
                print(msg)
                if tg:
                    tg.send(msg)
        print("10분 후 다시 확인합니다...\n")
        time.sleep(600)

if __name__ == "__main__":
    main()
