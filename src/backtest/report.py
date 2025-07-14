import pandas as pd
import matplotlib.pyplot as plt

class BacktestReport:
    def __init__(self, history):
        self.history = pd.DataFrame(history)

    def summary(self):
        # 누적 수익률, MDD 등 요약
        start = self.history['total_value'].iloc[0]
        end = self.history['total_value'].iloc[-1]
        ret = (end - start) / start
        summary_text = f"누적 수익률: {ret*100:.2f}%"
        print(summary_text)
        return summary_text
        # 추가 지표 계산 가능

    def plot(self):
        self.history.set_index('date')['total_value'].plot()
        plt.title('누적 수익률 곡선')
        plt.show()  # 이 줄이 반드시 필요합니다!
