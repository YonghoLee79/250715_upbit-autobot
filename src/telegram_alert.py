import requests

class TelegramAlert:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send(self, message):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": message}
        try:
            r = requests.post(url, data=data)
            if r.status_code == 200:
                print("[텔레그램] 전송 성공:", r.text)
            else:
                print(f"[텔레그램] 전송 실패 (status {r.status_code}):", r.text)
        except Exception as e:
            import traceback
            print("[텔레그램] 전송 예외 발생:", e)
            traceback.print_exc()
