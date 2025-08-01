def send_kakao_message(text):
    """
    카카오톡 알림톡/친구톡/푸시 메시지 전송 예시 (실제 사용시 카카오 비즈니스 인증, 토큰, 발신자/수신자 세팅 필요)
    환경변수에 KAKAO_TOKEN, KAKAO_PHONE, KAKAO_SENDER_KEY 등 필요
    """
    import os
    import requests
    KAKAO_TOKEN = os.getenv('KAKAO_TOKEN', '')
    KAKAO_PHONE = os.getenv('KAKAO_PHONE', '')  # 본인 전화번호 (수신자)
    KAKAO_SENDER_KEY = os.getenv('KAKAO_SENDER_KEY', '')  # 플러스친구/알림톡 발신 프로필 키
    if not (KAKAO_TOKEN and KAKAO_PHONE and KAKAO_SENDER_KEY):
        print('[카카오톡] 환경변수 미설정, 메시지 전송 생략')
        return
    url = 'https://kakaoapi.aligo.in/akv10/alimtalk/send/'  # 예시: 알리고 알림톡 API
    data = {
        'apikey': KAKAO_TOKEN,
        'userid': 'your_aligo_id',  # 알리고 계정 ID
        'senderkey': KAKAO_SENDER_KEY,
        'tpl_code': 'KA01TP230123456789',  # 템플릿 코드(사전 등록 필요)
        'sender': '발신번호',
        'receiver_1': KAKAO_PHONE,
        'recvname_1': '본인',
        'subject_1': '업비트 오토봇',
        'message_1': text,
    }
    try:
        r = requests.post(url, data=data)
        print('[카카오톡] 전송 결과:', r.text)
    except Exception as e:
        print('[카카오톡] 전송 오류:', e)
import os
from dotenv import load_dotenv
from upbit_api import UpbitAPI
from strategy import simple_monthly_target_strategy
from portfolio import get_krw_markets, get_monthly_returns, select_portfolio
import statistics
import time
import math
import datetime
import requests
from telegram_alert import TelegramAlert
import json
from flask import Flask, render_template

import csv
import streamlit as st

# 환경변수 로드
load_dotenv()

UPBIT_ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY')
UPBIT_SECRET_KEY = os.getenv('UPBIT_SECRET_KEY')
UPBIT_MARKET = os.getenv('UPBIT_MARKET', 'KRW-BTC')
START_BALANCE = 100000

# 수수료 설정 (업비트 기준)
TRADING_FEE = 0.0005  # 0.05%
EXCHANGE_FEE = 0.001  # 예시 환전 수수료 0.1%

# 매매 기록용 딕셔너리 및 횟수 제한
last_trade_time = {}
trade_count_per_day = {}

# 최소 기대수익률(예: 0.3%)
MIN_EXPECTED_PROFIT = 0.003
# 1일 최대 매매 횟수 제한 (제한 없음)
MAX_TRADES_PER_DAY = float('inf')

state_path = "coin_states.json"

app = Flask(__name__, template_folder='templates')

@app.route('/')
def status():
    state_path = os.path.join(os.path.dirname(__file__), "coin_states.json")
    with open(state_path) as f:
        coin_states = json.load(f)
    return render_template("status.html", coin_states=coin_states)

def load_coin_states():
    try:
        with open(state_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_coin_states(states):
    with open(state_path, "w") as f:
        json.dump(states, f, ensure_ascii=False, indent=2)

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


def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def safe_api_call(func, *args, **kwargs):
    for _ in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"API 오류: {e}")
            time.sleep(5)
    print(f"[치명적 오류] {func.__name__} 3회 연속 실패")
    # 텔레그램/이메일 알림 등 추가
    return None

def check_order_status(api, uuid):
    # 업비트 주문 조회 API 사용
    order = safe_api_call(api.get_order, uuid)
    if order is None:
        return "unknown"
    if order['state'] == 'done':
        return "filled"
    elif order['state'] == 'wait':
        return "pending"
    elif order['state'] == 'cancel':
        return "cancelled"
    else:
        return order['state']



def save_trade_history(row):
    file_path = os.path.join(os.path.dirname(__file__), "trade_history.csv")
    file_exists = os.path.isfile(file_path)
    with open(file_path, "a", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

class UpbitBot:
    def __init__(self):
        print(f"업비트 자동매매 오토봇 시작: {UPBIT_MARKET}")
        if not UPBIT_ACCESS_KEY or not UPBIT_SECRET_KEY:
            raise ValueError("UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY를 .env에 설정하세요.")
        self.api = UpbitAPI(str(UPBIT_ACCESS_KEY), str(UPBIT_SECRET_KEY))
        TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
        TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
        self.tg = None
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            self.tg = TelegramAlert(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        
        self.coin_states = load_coin_states()  # ← 이 줄을 추가하세요

        param_path = os.path.join(os.path.dirname(__file__), "strategy_params.json")
        if os.path.exists(param_path):
            with open(param_path) as f:
                params = json.load(f)
            MIN_EXPECTED_PROFIT = params.get("MIN_EXPECTED_PROFIT", 0.003)
            MAX_TRADES_PER_DAY = float('inf')  # 제한 없음
            TOP_N = params.get("TOP_N", 5)
        else:
            MIN_EXPECTED_PROFIT = 0.003
            MAX_TRADES_PER_DAY = float('inf')  # 제한 없음
            TOP_N = 5

    def run(self):
        while True:
            self.trade()

    def trade(self):
        param_path = os.path.join(os.path.dirname(__file__), "strategy_params.json")
        if os.path.exists(param_path):
            with open(param_path) as f:
                params = json.load(f)
            MIN_EXPECTED_PROFIT = params.get("MIN_EXPECTED_PROFIT", 0.003)
            MAX_TRADES_PER_DAY = float('inf')
            TOP_N = params.get("TOP_N", 5)
        else:
            MIN_EXPECTED_PROFIT = 0.003
            MAX_TRADES_PER_DAY = float('inf')
            TOP_N = 5

        # 1. 잔고조회에 예외처리 적용
        balances = safe_api_call(self.api.get_balance)
        if balances is None:
            return

        # 2. 시세조회에 예외처리 적용
        tickers = []
        total_krw = 0.0
        for b in balances:
            if b['currency'] == 'KRW':
                total_krw += float(b['balance'])
            elif float(b['balance']) > 0:
                tickers.append(f"KRW-{b['currency']}")
        if tickers:
            prices = safe_api_call(self.api.get_ticker, ",".join(tickers))
            if prices is None:
                return
            if isinstance(prices, dict):
                prices = [prices]
            for b, t in zip(balances, prices):
                if b['currency'] == t['market'].split('-')[1]:
                    total_krw += float(b['balance']) * float(t['trade_price'])

        msg = f"[업비트 오토봇] 전체 평가금액(원화+코인): {total_krw:.2f} KRW"
        print(msg)
        if self.tg:
            self.tg.send(msg)
        if total_krw < 5000:
            print("매수 가능한 평가금액이 부족합니다.")
            time.sleep(60)
            return

        # 여기에 선언!
        max_per_coin = total_krw * 0.2

        # 기준자산을 매번 현재 자산으로 갱신
        if not hasattr(self, 'initial_krw') or self.initial_krw == 0:
            self.initial_krw = total_krw

        loss_rate = (total_krw - self.initial_krw) / self.initial_krw
        msg = f"누적 수익률: {loss_rate*100:.2f}% (기준자산: {self.initial_krw:.2f} KRW)"
        print(msg)
        if self.tg:
            self.tg.send(msg)
        if loss_rate < -0.10:
            msg = "누적 손실 -10% 초과! 전체 자산 현금화(매도) 실행"
            print(msg)
            if self.tg:
                self.tg.send(msg)
            # 전체 코인 시장가 매도
            for b in balances:
                if b['currency'] != 'KRW' and float(b['balance']) > 0:
                    market = f"KRW-{b['currency']}"
                    msg = f"시장가 전량매도: {market} {b['balance']}개"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    sell_result = self.api.sell_market_order(market, float(b['balance']))
                    msg = f"매도 결과: {sell_result}"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
            msg = "10분 후 재시작"
            print(msg)
            if self.tg:
                self.tg.send(msg)
            time.sleep(600)
            return
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
            prices = [c['trade_price'] for c in candles]
            vols = [c['candle_acc_trade_price'] for c in candles]
            price_30d_ago = prices[-1]
            price_now = prices[0]
            ret = (price_now - price_30d_ago) / price_30d_ago
            volatility = statistics.stdev(prices)
            avg_vol = statistics.mean(vols)

            # 이동평균 (MA5, MA20)
            ma5 = sum(prices[:5]) / 5
            ma20 = sum(prices[:20]) / 20

            # 볼린저밴드 (20일)
            bb_ma = ma20
            bb_std = statistics.stdev(prices[:20])
            bb_upper = bb_ma + 2 * bb_std
            bb_lower = bb_ma - 2 * bb_std

            # RSI 계산
            deltas = [prices[i] - prices[i+1] for i in range(len(prices)-1)]
            gains = [d for d in deltas if d > 0]
            losses = [-d for d in deltas if d < 0]
            avg_gain = sum(gains)/14 if len(gains)>=14 else 0.0001
            avg_loss = sum(losses)/14 if len(losses)>=14 else 0.0001
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))

            # 트레일링 스탑(예시: 10% 이상 수익 후 고점 대비 5% 하락 시 매도)
            trailing_stop = False
            if market in self.coin_states and self.coin_states[market]["buy_price"]:
                buy_price = float(self.coin_states[market]["buy_price"])
                highest = max(prices)
                if price_now > buy_price * 1.10 and price_now < highest * 0.95:
                    trailing_stop = True

            # 고급 스코어 계산
            score = (
                ret * 0.4 +  # 수익률
                ((ma5 - ma20) / ma20) * 0.2 +  # 단기/장기 이동평균 갭
                (rsi < 30) * 0.1 +  # 과매도 신호
                ((price_now < bb_lower) * 0.1) +  # 볼린저밴드 하단 돌파
                (avg_vol/1e9) * 0.1 -  # 거래량
                (volatility/abs(ret) if ret!=0 else 0) * 0.1  # 변동성
            )
            returns.append({
                "market": market,
                "return": ret,
                "volatility": volatility,
                "avg_vol": avg_vol,
                "rsi": rsi,
                "ma5": ma5,
                "ma20": ma20,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "score": score,
                "trailing_stop": trailing_stop
            })

        # 전체 시장 평균 수익률로 하락장 필터링
        market_avg = statistics.mean([r['return'] for r in returns])
        today = get_today()
        if today not in trade_count_per_day:
            trade_count_per_day[today] = {}
        if market_avg < -0.05:
            print("시장 전체가 하락장입니다. 현금 비중을 80%로 유지하고, RSI 30 이하 반등 신호 종목만 소액 매수/코인빌려주기 실행")
            # 현금 80% 유지, 20%만 rsi_targets에 분산
            invest_amount = total_krw * 0.2
            if rsi_targets:
                amount_per_coin = max(5000, min(invest_amount // len(rsi_targets), max_per_coin))
                for t in rsi_targets:
                    now = time.time()
                    # 30분 이내 동일 코인 재매매 방지
                    if t['market'] in last_trade_time and now - last_trade_time[t['market']] < 1800:
                        msg = f"{t['market']} : 최근 30분 내 매매 이력, 매수 생략"
                        print(msg)
                        if self.tg:
                            self.tg.send(msg)
                        continue
                    # 1일 최대 매매 횟수 제한
                    if trade_count_per_day[today].get(t['market'], 0) >= MAX_TRADES_PER_DAY:
                        msg = f"{t['market']} : 1일 최대 매매 횟수 초과, 매수 생략"
                        print(msg)
                        if self.tg:
                            self.tg.send(msg)
                        continue
                    # 최소 기대수익률 조건(예시: 0.3%)
                    expected_profit = t['ret']
                    if expected_profit < MIN_EXPECTED_PROFIT:
                        msg = f"{t['market']} : 기대수익률 {expected_profit*100:.2f}% 미만, 매수 생략"
                        print(msg)
                        if self.tg:
                            self.tg.send(msg)
                        continue
                    if amount_per_coin < 5000:
                        msg = f"{t['market']} : {amount_per_coin} KRW (최소주문금액 미만, 매수 생략)"
                        print(msg)
                        if self.tg:
                            self.tg.send(msg)
                        continue
                    msg = f"[반등신호] {t['market']} : {amount_per_coin} KRW 매수 시도 및 코인빌려주기(렌딩) 실행"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    buy_result = self.api.buy_market_order(t['market'], amount_per_coin)
                    save_trade_history({
                        "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "buy",
                        "market": t['market'],
                        "amount": amount_per_coin,
                        "price": buy_result.get("price") if isinstance(buy_result, dict) else None,
                        "volume": buy_result.get("volume") if isinstance(buy_result, dict) else None,
                        "result": str(buy_result)
                    })
                    # --- 코인빌리기(렌딩) 자동화 예시 ---
                    # 실제 업비트 렌딩 API가 있다면 아래처럼 호출
                    # self.api.lend_coin(t['market'], amount_per_coin, lend_ratio=0.8, period=7)
                    # 아래는 수동 신청 안내 메시지
                    msg = f"[코인빌리기] {t['market']} {amount_per_coin}원 상당 코인 렌딩 신청: 업비트 렌딩 페이지에서 담보비율 80%로 신청하세요."
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    last_trade_time[t['market']] = now
                    trade_count_per_day[today][t['market']] = trade_count_per_day[today].get(t['market'], 0) + 1
                    msg = f"실제 매수 결과: {buy_result}"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    # 매수/매도 직후에 아래 코드 추가
                    coin_states = load_coin_states()
                    m = t['market']
                    if m not in coin_states:
                        coin_states[m] = {
                            "buy_price": None,
                            "bought_volume": 0,
                            "last_trade_time": 0,
                            "trade_count_today": 0,
                            "order_status": ""
                        }
                    coin_states[m]["buy_price"] = buy_result.get("price") if isinstance(buy_result, dict) else None
                    coin_states[m]["bought_volume"] = buy_result.get("volume") if isinstance(buy_result, dict) else None
                    coin_states[m]["last_trade_time"] = now
                    coin_states[m]["trade_count_today"] = trade_count_per_day[today][m]
                    coin_states[m]["order_status"] = "filled"  # 실제 체결 상태로 변경 가능
                    save_coin_states(coin_states)
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
                now = time.time()
                # 30분 이내 동일 코인 재매매 방지
                if p['market'] in last_trade_time and now - last_trade_time[p['market']] < 1800:
                    msg = f"{p['market']} : 최근 30분 내 매매 이력, 매수 생략"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    continue
                # 1일 최대 매매 횟수 제한
                if trade_count_per_day[today].get(p['market'], 0) >= MAX_TRADES_PER_DAY:
                    msg = f"{p['market']} : 1일 최대 매매 횟수 초과, 매수 생략"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    continue
                # 최소 기대수익률 조건(예: 0.3%)
                expected_profit = p['return']
                if expected_profit < MIN_EXPECTED_PROFIT:
                    msg = f"{p['market']} : 기대수익률 {expected_profit*100:.2f}% 미만, 매수 생략"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    continue
                if amount < 5000:
                    msg = f"{p['market']} : {amount} KRW (최소주문금액 미만, 매수 생략)"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
                    continue
                msg = f"{p['market']} : {amount} KRW (최대비중 적용)"
                print(msg)
                if self.tg:
                    self.tg.send(msg)
                buy_result = self.api.buy_market_order(p['market'], amount)
                save_trade_history({
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "buy",
                    "market": p['market'],
                    "amount": amount,
                    "price": buy_result.get("price") if isinstance(buy_result, dict) else None,
                    "volume": buy_result.get("volume") if isinstance(buy_result, dict) else None,
                    "result": str(buy_result)
                })
                # --- 코인빌리기(렌딩) 자동화 예시 ---
                # 실제 업비트 렌딩 API가 있다면 아래처럼 호출
                # self.api.lend_coin(p['market'], amount, lend_ratio=0.8, period=7)
                # 아래는 수동 신청 안내 메시지
                msg = f"[코인빌리기] {p['market']} {amount}원 상당 코인 렌딩 신청: 업비트 렌딩 페이지에서 담보비율 80%로 신청하세요."
                print(msg)
                if self.tg:
                    self.tg.send(msg)
                last_trade_time[p['market']] = now
                trade_count_per_day[today][p['market']] = trade_count_per_day[today].get(p['market'], 0) + 1
                msg = f"실제 매수 결과: {buy_result}"
                print(msg)
                if self.tg:
                    self.tg.send(msg)
                # 매수/매도 직후에 아래 코드 추가
                coin_states = load_coin_states()
                m = p['market']
                if m not in coin_states:
                    coin_states[m] = {
                        "buy_price": None,
                        "bought_volume": 0,
                        "last_trade_time": 0,
                        "trade_count_today": 0,
                        "order_status": ""
                    }
                coin_states[m]["buy_price"] = buy_result.get("price") if isinstance(buy_result, dict) else None
                coin_states[m]["bought_volume"] = buy_result.get("volume") if isinstance(buy_result, dict) else None
                coin_states[m]["last_trade_time"] = now
                coin_states[m]["trade_count_today"] = trade_count_per_day[today][m]
                coin_states[m]["order_status"] = "filled"  # 실제 체결 상태로 변경 가능
                save_coin_states(coin_states)

            # --- 메일/텔레그램 알림: 수익 발생(익절/매도) 시 ---
            buy_result = None
            try:
                # 알림 메시지 생성 전에 coin_states가 항상 정의되도록 보장
                if 'coin_states' not in locals():
                    coin_states = load_coin_states()
                subject = "[업비트 오토봇 알림] 수익실현/매도"
                m = market
                buy_price = None
                volume = None
                sell_price = None
                realized_profit = None
                profit_rate = None
                if m in coin_states:
                    buy_price = coin_states[m].get("buy_price")
                    volume = coin_states[m].get("bought_volume")
                if isinstance(buy_result, dict):
                    sell_price = buy_result.get("price")
                    if not volume:
                        volume = buy_result.get("volume")
                if buy_price and sell_price and volume:
                    realized_profit = (float(sell_price) - float(buy_price)) * float(volume)
                    profit_rate = (float(sell_price) - float(buy_price)) / float(buy_price) * 100
                body = f"{market} 매도, 수익 발생! (자동매매)\n"
                if buy_price and sell_price and volume:
                    body += f"매수가: {buy_price} / 매도가: {sell_price} / 수량: {volume}\n실현수익: {realized_profit:.0f}원 (수익률: {profit_rate:.2f}%)\n"
                body += f"상세내역: {buy_result}"
                # 메일 발송 코드 완전 삭제
                if self.tg:
                    self.tg.send(f"{subject}\n{body}")
            except Exception as e:
                print('[수익 알림 오류]', e)
            # 현재 보유 코인 목록
            current_holdings = [b['currency'] for b in balances if b['currency'] != 'KRW' and float(b['balance']) > 0]
            coin_states = load_coin_states()  # ← UnboundLocalError 방지: 항상 정의
            # 새 포트폴리오에 없는 코인은 전량 매도
            for holding in current_holdings:
                market = f"KRW-{holding}"
                if market not in [p['market'] for p in portfolio]:
                    buy_price = float(coin_states[market]["buy_price"])
                    current_price = ... # 현재가 조회
                    if current_price > buy_price * 1.05:
                        amount = float([b for b in balances if b['currency'] == holding][0]['balance']) / 2
                        msg = f"{market} : 5% 이상 수익, 절반 익절"
                        # --- 메일/텔레그램 알림: 수익 발생 ---
                        subject = "[업비트 오토봇 알림] 수익실현/익절"
                        # 매도 상세 정보 계산
                        try:
                            m = market
                            buy_price = None
                            volume = None
                            sell_price = None
                            realized_profit = None
                            profit_rate = None
                            if m in coin_states:
                                buy_price = coin_states[m].get("buy_price")
                                volume = coin_states[m].get("bought_volume")
                            if isinstance(sell_result, dict):
                                sell_price = sell_result.get("price")
                                if not volume:
                                    volume = sell_result.get("volume")
                            if buy_price and sell_price and volume:
                                realized_profit = (float(sell_price) - float(buy_price)) * float(volume)
                                profit_rate = (float(sell_price) - float(buy_price)) / float(buy_price) * 100
                            body = f"{market} 5% 이상 수익, 절반 익절!\n"
                            if buy_price and sell_price and volume:
                                body += f"매수가: {buy_price} / 매도가: {sell_price} / 수량: {volume}\n실현수익: {realized_profit:.0f}원 (수익률: {profit_rate:.2f}%)\n"
                            body += f"상세내역: {sell_result if 'sell_result' in locals() else ''}"
                        except Exception as e:
                            body = f"{market} 5% 이상 수익, 절반 익절!\n상세내역: {sell_result if 'sell_result' in locals() else ''}"
                        # 메일 발송 코드 완전 삭제
                        try:
                            if self.tg:
                                self.tg.send(f"{subject}\n{body}")
                        except Exception as e:
                            print('[텔레그램] 수익 알림 실패:', e)
                    else:
                        amount = float([b for b in balances if b['currency'] == holding][0]['balance'])
                        msg = f"{market} : 포트폴리오 제외, 전량 매도"
                        # --- 메일/텔레그램 알림: 포트폴리오 제외 매도 ---
                        subject = "[업비트 오토봇 알림] 포트폴리오 제외 매도"
                        # 매도 상세 정보 계산
                        try:
                            m = market
                            buy_price = None
                            volume = None
                            sell_price = None
                            realized_profit = None
                            profit_rate = None
                            if m in coin_states:
                                buy_price = coin_states[m].get("buy_price")
                                volume = coin_states[m].get("bought_volume")
                            if isinstance(sell_result, dict):
                                sell_price = sell_result.get("price")
                                if not volume:
                                    volume = sell_result.get("volume")
                            if buy_price and sell_price and volume:
                                realized_profit = (float(sell_price) - float(buy_price)) * float(volume)
                                profit_rate = (float(sell_price) - float(buy_price)) / float(buy_price) * 100
                            body = f"{market} 포트폴리오 제외, 전량 매도!\n"
                            if buy_price and sell_price and volume:
                                body += f"매수가: {buy_price} / 매도가: {sell_price} / 수량: {volume}\n실현수익: {realized_profit:.0f}원 (수익률: {profit_rate:.2f}%)\n"
                            body += f"상세내역: {sell_result if 'sell_result' in locals() else ''}"
                        except Exception as e:
                            body = f"{market} 포트폴리오 제외, 전량 매도!\n상세내역: {sell_result if 'sell_result' in locals() else ''}"
                        # 메일 발송 코드 완전 삭제
                        try:
                            if self.tg:
                                self.tg.send(f"{subject}\n{body}")
                        except Exception as e:
                            print('[텔레그램] 매도 알림 실패:', e)
                    # 매도 실행
                    sell_result = self.api.sell_market_order(market, amount)
                    msg = f"매도 결과: {sell_result}"
                    print(msg)
                    if self.tg:
                        self.tg.send(msg)
            # 이후 새 포트폴리오 종목만 매수
        print("1분 후 다시 확인합니다...\n")
        time.sleep(60)

def select_portfolio(returns, total_krw, min_amount=5000, top_n=5):
    selected = []
    for r in returns[:top_n]:
        amount = max(min_amount, total_krw // top_n)
        selected.append({
            'market': r['market'],
            'amount': amount,
            'return': r['return']  # ← 이 부분 추가
        })
    return selected

# dashboard_streamlit.py
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

if __name__ == "__main__":
    # 메일/텔레그램 발송 테스트
    # 메일 발송 테스트 비활성화, 텔레그램만 테스트
    try:
        from telegram_alert import TelegramAlert
        import os
        TelegramAlert(os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID')).send('업비트 오토봇 텔레그램 발송 테스트입니다.')
    except Exception as e:
        print(f"텔레그램 발송 테스트 실패: {e}")

    # 실제 자동매매 실행
    try:
        bot = UpbitBot()
        bot.run()
    except Exception as e:
        print(f"[오토봇 오류/정지] {e}")
        # 메일 발송 코드 완전 삭제
        try:
            if 'bot' in locals() and hasattr(bot, 'tg') and bot.tg:
                bot.tg.send(f"[업비트 오토봇 오류/정지]\n{str(e)}")
        except Exception as e3:
            print('[텔레그램] 오류/정지 알림 실패:', e3)
