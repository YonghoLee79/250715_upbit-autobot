import requests

class TelegramAlert:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(self, message):
        data = {
            "chat_id": self.chat_id,
            "text": message
        }
        try:
            res = requests.post(self.api_url, data=data, timeout=5)
            print("[텔레그램 응답]", res.text)  # 응답 확인용
        except Exception as e:
            print(f"[텔레그램 알림 오류] {e}")
