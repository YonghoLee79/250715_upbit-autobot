import pandas as pd
import os

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def get_ohlcv(self, market: str, start: str, end: str) -> pd.DataFrame:
        """
        지정한 마켓의 일별 OHLCV 데이터 반환 (start, end: 'YYYY-MM-DD')
        실제 구현에서는 Upbit API 또는 csv/pickle 등에서 로드
        """
        # 예시: 임시 더미 데이터
        dates = pd.date_range(start, end)
        df = pd.DataFrame({
            'date': dates,
            'open': 1000,
            'high': 1100,
            'low': 900,
            'close': 1050,
            'volume': 1000
        })
        df.set_index('date', inplace=True)
        return df
