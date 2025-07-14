import os
import time
import logging
import json
from dotenv import load_dotenv
from upbit_api import UpbitAPI
from ai_verifier import AIVerifier
from telegram_alert import TelegramAlert
from email_alert import EmailAlert
from flask import Flask, render_template

app = Flask(__name__, template_folder='templates')

def get_current_price(upbit, market):
    ticker = upbit.get_ticker(market)
    return ticker['trade_price'] if ticker else None

def safe_api_call(func, *args, **kwargs):
    for _ in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"API 오류: {e}")
            time.sleep(5)
    # 치명적 오류 발생 시 알림
    if tg:
        tg.send(f"[치명적 오류] {func.__name__} 3회 연속 실패")
    if emailer:
        emailer.send("[치명적 오류]", f"{func.__name__} 3회 연속 실패")
    raise Exception("API 3회 연속 실패")

def save_state(states, filename="state.json"):
    with open(filename, "w") as f:
        json.dump(states, f)

def load_state(filename="state.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}

@app.route('/')
def status():
    state_path = os.path.join(os.path.dirname(__file__), "state.json")
    with open(state_path) as f:
        coin_states = json.load(f)
    return render_template("status.html", coin_states=coin_states)

def main():
    load_dotenv()
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")
    markets = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    openai_key = os.getenv("OPENAI_API_KEY")
    email_host = os.getenv("EMAIL_HOST")
    email_port = int(os.getenv("EMAIL_PORT", "465"))
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    email_to = os.getenv("EMAIL_TO")

    # 추가: 코인별 전략 파라미터와 AI 프롬프트
    strategy_params = {
        "KRW-BTC": {"buy_amount": 10000, "stop_loss": 0.05, "take_profit": 0.1},
        "KRW-ETH": {"buy_amount": 20000, "stop_loss": 0.03, "take_profit": 0.08},
        "KRW-XRP": {"buy_amount": 5000,  "stop_loss": 0.07, "take_profit": 0.15},
    }
    ai_prompts = {
        "KRW-BTC": "비트코인 시장 상황을 분석하고 매수 신호가 있는지 한 문장으로 답해줘.",
        "KRW-ETH": "이더리움의 단기 상승 가능성을 한 문장으로 평가해줘.",
        "KRW-XRP": "리플의 변동성에 주의해야 할지 한 문장으로 알려줘."
    }

    upbit = UpbitAPI(access_key, secret_key)
    ai = AIVerifier(openai_api_key=openai_key)
    tg = TelegramAlert(telegram_token, telegram_chat_id) if telegram_token and telegram_chat_id else None
    emailer = EmailAlert(email_host, email_port, email_user, email_pass, email_to) if email_host and email_user and email_pass and email_to else None

    coin_states = load_state()
    coin_states = {m: {"buy_price": None, "bought_volume": 0, "last_trade_price": None} for m in markets}

    # 일일 손실 제한을 위한 변수
    total_daily_loss = 0
    daily_loss_limit = -0.1  # 하루 손실 한도 (-10%)

    while True:
        for market in markets:
            params = strategy_params[market]
            prompt = ai_prompts[market]
            state = coin_states.get(market, {"buy_price": None, "bought_volume": 0, "last_trade_price": None})

            # 1. AI 검증
            is_positive, answer = ai.llm_check(prompt)
            if not is_positive:
                continue

            # 2. 기술적 지표/조건 체크 (필요시 추가)

            # 3. 손절/익절 체크
            price = get_current_price(upbit, market)
            if state["buy_price"] and state["bought_volume"] > 0:
                change = (price - state["buy_price"]) / state["buy_price"]
                if change <= -params["stop_loss"]:
                    # 손절 매도
                    sell_result = upbit.sell_market_order(market, state["bought_volume"])
                    state["buy_price"] = None
                    state["bought_volume"] = 0
                    state["last_trade_price"] = price
                    # 알림/저장 등
                    continue
                elif change >= params["take_profit"]:
                    # 익절 매도
                    sell_result = upbit.sell_market_order(market, state["bought_volume"])
                    state["buy_price"] = None
                    state["bought_volume"] = 0
                    state["last_trade_price"] = price
                    # 알림/저장 등
                    continue

            # 4. 매수 조건
            if is_positive and state["bought_volume"] == 0:
                order_result = upbit.buy_market_order(market, params["buy_amount"])
                state["buy_price"] = price
                state["bought_volume"] = order_result.get('volume', 0)
                state["last_trade_price"] = price
                # 알림/저장 등

            coin_states[market] = state

        save_state(coin_states)
        time.sleep(60)

if __name__ == '__main__':
    main()
    app.run(port=5000)