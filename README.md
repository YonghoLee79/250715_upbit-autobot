# Upbit Autobot

## 소개
Upbit Autobot은 업비트 거래소에서 여러 코인을 동시에 자동매매할 수 있는 멀티코인 AI 트레이딩 봇입니다.  
AI 기반 신호, 코인별 전략 파라미터, 손절/익절, 실시간 대시보드, 텔레그램/이메일 알림 등  
실전 자동매매에 필요한 다양한 기능을 제공합니다.

---

## 주요 기능

- **멀티코인 전략**: 여러 코인을 동시에 독립적으로 자동매매
- **코인별 전략/파라미터**: 코인마다 매수금액, 손절/익절 비율, AI 프롬프트 개별 설정
- **AI 기반 1차 검증**: OpenAI GPT를 활용한 매수 신호 판단
- **손절/익절 자동 매도**: 매수 후 지정 수익률/손실률 도달 시 자동 매도
- **실시간 대시보드**: Flask 기반 웹에서 코인별 상태 실시간 확인
- **알림**: 텔레그램/이메일로 체결, 오류 등 주요 이벤트 알림
- **상태 저장/복구**: 코인별 상태를 파일로 저장, 재시작 시 복구

---

## 폴더/파일 구조

```
upbit-autobot/
├── .env
├── src/
│   ├── realtrade_main.py
│   ├── state.json
│   ├── upbit_api.py
│   ├── ai_verifier.py
│   ├── telegram_alert.py
│   ├── email_alert.py
│   ├── logger.py
│   └── templates/
│       └── status.html
```

---

## 환경설정

1. **.env 파일 작성**
    ```
    UPBIT_ACCESS_KEY=...
    UPBIT_SECRET_KEY=...
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
    OPENAI_API_KEY=...
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=465
    EMAIL_USER=your_email@gmail.com
    EMAIL_PASS=your_app_password
    EMAIL_TO=your_email@gmail.com
    ```

2. **필수 패키지 설치**
    ```bash
    pip install flask python-dotenv
    ```

---

## 실행 방법

1. **자동매매 및 대시보드 실행**
    ```bash
    cd src
    python realtrade_main.py
    ```
2. **웹 대시보드 접속**
    - 브라우저에서 [http://localhost:5000](http://localhost:5000) 접속

---

## 주요 코드 구조

- **코인별 전략 파라미터/프롬프트**
    ```python
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
    ```

- **메인 루프**
    - 각 코인별로 AI 검증 → 손절/익절 체크 → 매수/매도 실행 → 상태 저장

---

## 참고/주의사항

- **실제 자산이 거래되므로 반드시 소액으로 충분히 테스트 후 사용하세요.**
- API 키, 이메일 비밀번호 등 민감 정보는 외부에 노출되지 않도록 주의하세요.
- state.json, .env 파일은 .gitignore에 추가하세요.
- 실매매 전에는 페이퍼트레이딩(모의매매)로 충분히 검증하세요.

---

## 향후 발전 방향

- 클래스 기반 구조, 포트폴리오 리밸런싱, 고급 리스크 관리, 실시간 파라미터 변경,  
  체결/미체결 관리, 대시보드 고도화 등 전문 트레이딩 시스템으로 확장
