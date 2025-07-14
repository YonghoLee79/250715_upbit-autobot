import pandas as pd

class BacktestSimulator:
    def __init__(self, initial_balance, fee_rate=0.0005, max_coin_ratio=0.2, max_loss=-0.1, slippage=0.001, min_volume=10000000):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.max_coin_ratio = max_coin_ratio
        self.max_loss = max_loss
        self.slippage = slippage  # 슬리피지(체결가 오차)
        self.min_volume = min_volume  # 최소 거래대금(예: 1천만원)
        self.reset()

    def reset(self):
        self.balance = self.initial_balance
        self.positions = {}
        self.history = []
        self.total_value = self.initial_balance
        self.max_drawdown = 0

    def run(self, strategy_fn, data_dict, rebalance_dates):
        for date in rebalance_dates:
            orders = strategy_fn(date, self.positions, self.balance, data_dict)

            # 1. 렌딩(코인빌려주기) 전략 처리
            if 'LENDING' in orders:
                daily_rate = orders['LENDING']
                self.balance *= (1 + daily_rate)
                self.positions = {}  # 모든 코인 청산
                # 평가금액 = 현금
                self.total_value = self.balance
            else:
                # 2. 기존 포지션 전량 매도(리밸런싱)
                for market, amount in list(self.positions.items()):
                    if amount > 0 and market in data_dict and date in data_dict[market].index:
                        price = data_dict[market].loc[date]['close']
                        # 슬리피지 적용(매도는 -)
                        price *= (1 - self.slippage)
                        proceeds = amount * price
                        proceeds -= proceeds * self.fee_rate
                        self.balance += proceeds
                self.positions = {}

                # 3. 매수(목표 포트폴리오)
                for market, amount in orders.items():
                    if market in data_dict and date in data_dict[market].index and amount > 0:
                        price = data_dict[market].loc[date]['close']
                        # 거래량 필터
                        volume = data_dict[market].loc[date]['value'] if 'value' in data_dict[market].columns else None
                        if volume is not None and volume < self.min_volume:
                            continue
                        # 슬리피지 적용(매수는 +)
                        price *= (1 + self.slippage)
                        cost = amount * price
                        if cost > self.balance:
                            amount = int(self.balance // price)
                            cost = amount * price
                        if amount > 0 and cost > 0:
                            # 최대 비중 제한
                            if cost > self.initial_balance * self.max_coin_ratio:
                                cost = self.initial_balance * self.max_coin_ratio
                                amount = int(cost // price)
                                cost = amount * price
                            if amount > 0 and cost > 0:
                                self.balance -= cost
                                self.balance -= cost * self.fee_rate
                                # 잔돈(소수점 이하) 버림
                                self.positions[market] = int(amount)

                # 4. 평가금액 계산
                total_value = self.balance
                for market, amount in self.positions.items():
                    if market in data_dict and date in data_dict[market].index:
                        price = data_dict[market].loc[date]['close']
                        total_value += amount * price
                self.total_value = total_value

            # 5. 최대 손실(청산) 체크
            ret = (self.total_value - self.initial_balance) / self.initial_balance
            if ret <= self.max_loss:
                self.balance = self.total_value
                self.positions = {}
                self.total_value = self.balance

            # 6. 기록
            self.history.append({
                'date': date,
                'balance': self.balance,
                'positions': self.positions.copy(),
                'total_value': self.total_value
            })
        return self.history
