import hashlib
import requests
import jwt
import uuid
import time
import os
from urllib.parse import urlencode

from typing import Optional, Dict, Any

class UpbitAPI:
    def __init__(self, access_key: str, secret_key: str) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.server_url = "https://api.upbit.com"

    def _get_headers(self, query: Optional[str] = None) -> Dict[str, str]:
        payload: Dict[str, Any] = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        if query:
            m = hashlib.sha512()
            m.update(query.encode('utf-8'))
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        authorize_token = f'Bearer {jwt_token}'
        headers = {"Authorization": authorize_token}
        return headers

    def get_balance(self) -> Any:
        url = self.server_url + "/v1/accounts"
        headers = self._get_headers()
        res = requests.get(url, headers=headers)
        return res.json()

    def get_ticker(self, market: str) -> Any:
        url = self.server_url + f"/v1/ticker?markets={market}"
        res = requests.get(url)
        return res.json()[0]

    def buy_market_order(self, market: str, amount: float) -> Any:
        url = self.server_url + "/v1/orders"
        params = {
            'market': market,
            'side': 'bid',
            'price': str(amount),
            'ord_type': 'price',
        }
        query = urlencode(params)
        headers = self._get_headers(query)
        res = requests.post(url, params=params, headers=headers)
        return res.json()

    def sell_market_order(self, market: str, volume: float) -> Any:
        url = self.server_url + "/v1/orders"
        params = {
            'market': market,
            'side': 'ask',
            'volume': str(volume),
            'ord_type': 'market',
        }
        query = urlencode(params)
        headers = self._get_headers(query)
        res = requests.post(url, params=params, headers=headers)
        return res.json()
