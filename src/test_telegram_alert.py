import os
from telegram_alert import TelegramAlert
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv(dotenv_path="../.env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[오류] .env에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID가 설정되어 있는지 확인하세요.")
    else:
        alert = TelegramAlert(token, chat_id)
        alert.send("[테스트] 텔레그램 알림이 정상적으로 동작합니다.")
