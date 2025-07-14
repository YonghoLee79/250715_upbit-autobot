from backtest.simulator import BacktestSimulator

def auto_optimize(strategy_fn, data_dict, rebalance_dates, param_grid):
    best_ret = -float('inf')
    best_param = None
    best_history = None

    for params in param_grid:
        sim = BacktestSimulator(
            initial_balance=1000000,
            max_coin_ratio=params.get('max_coin_ratio', 0.2)
        )
        test_dates = rebalance_dates[::params.get('rebalance_period', 30)]
        history = sim.run(
            lambda date, pos, bal, data: strategy_fn(date, pos, bal, data, params),
            data_dict,
            test_dates
        )
        start = history[0]['total_value']
        end = history[-1]['total_value']
        ret = (end - start) / start
        if ret > best_ret:
            best_ret = ret
            best_param = params
            best_history = history

    print(f"최적 파라미터: {best_param}, 예상 수익률: {best_ret:.2%}")
    return best_param, best_history