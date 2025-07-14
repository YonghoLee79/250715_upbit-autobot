import os
from dotenv import load_dotenv
from telegram_alert import TelegramAlert

load_dotenv()
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

if telegram_token and telegram_chat_id:
    tg = TelegramAlert(telegram_token, telegram_chat_id)
    tg.send("✅ 텔레그램 알림 테스트 메시지입니다.")
    print("텔레그램 메시지 전송 완료!")
else:
    print("텔레그램 토큰 또는 채팅 ID가 없습니다.")
