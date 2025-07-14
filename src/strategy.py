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
