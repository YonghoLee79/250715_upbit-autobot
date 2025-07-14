import os
import openai

class AIVerifier:
    def __init__(self, openai_api_key):
        self.api_key = openai_api_key

    def llm_check(self, prompt):
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
        # 간단한 긍정 판별 예시
        is_positive = ("매수" in answer) or ("긍정" in answer)
        return is_positive, answer