import os
from dotenv import load_dotenv
from upbit_api import UpbitAPI
from telegram_alert import TelegramAlert
import openai

def test_upbit():
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")
    try:
        api = UpbitAPI(access_key, secret_key)
        balance = api.get_balance()
        print("[Upbit] 잔고 조회 성공:", balance)
    except Exception as e:
        print("[Upbit] API 오류:", e)

def test_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    try:
        tg = TelegramAlert(token, chat_id)
        tg.send("✅ 텔레그램 알림 테스트 메시지입니다.")
        print("[Telegram] 메시지 전송 성공")
    except Exception as e:
        print("[Telegram] API 오류:", e)

def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "이 키가 정상인지 한글로 답해줘."}]
        )
        print("[OpenAI] 응답:", response.choices[0].message.content)
    except Exception as e:
        print("[OpenAI] API 오류:", e)

if __name__ == "__main__":
    load_dotenv()
    test_upbit()
    test_telegram()
    test_openai()