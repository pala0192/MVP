"""
config.py - 시장별 + 종목별 + 기간별 가중치 관리
"""
import json
import os

# 사전 정의 홀딩 기간 (표시 레이블 → 일수 변환)
HOLDING_PERIODS = {
    '6h':  0.25,
    '12h': 0.5,
    '1d':  1,
    '3d':  3,
    '7d':  7,
    '2w':  14,
    '4w':  28,
    '6w':  42,
    '8w':  56,
    '10w': 70,
    '12w': 84,
    '14w': 98,
    '16w': 112,
    '18w': 126,
    '20w': 140,
    '22w': 154,
    '24w': 168,
    '26w': 182,
    '28w': 196,
    '30w': 210,
}

def period_label_to_days(label: str) -> float:
    """'6h' → 0.25, '2w' → 14 등 변환"""
    return HOLDING_PERIODS.get(label, 30)



def _default_weights_for_days(days: float) -> dict:
    """기간별 기본 신호 가중치"""
    if days <= 1:           # 초단기
        return {'rsi': 0.20, 'stoch': 0.35, 'bollinger': 0.25, 'macd': 0.20}
    elif days <= 7:         # 단기
        return {'rsi': 0.30, 'stoch': 0.30, 'bollinger': 0.20, 'macd': 0.20}
    elif days <= 28:        # 중단기
        return {'macd': 0.40, 'ema20': 0.30, 'rsi': 0.20, 'bollinger': 0.10}
    elif days <= 84:        # 중기
        return {'macd': 0.35, 'ema20': 0.25, 'ema60': 0.20, 'rsi': 0.20}
    else:                   # 장기
        return {'ema60': 0.35, 'ema120': 0.25, 'macd': 0.20, 'atr': 0.20}


class Config:
    TICKER_WEIGHT_FILE = 'ticker_weights.json'

    def __init__(self):
        self.investment_mode = 'AUTO'
        self.initial_capital = 10_000_000

        # 20개의 지정된 기간별 독립 가중치 저장소
        self.base_weights = {
            label: _default_weights_for_days(days) 
            for label, days in HOLDING_PERIODS.items()
        }

        # 종목별 + 기간별 가중치: {ticker: {period_label: {signal: weight}}}
        self._ticker_weights: dict = {}

    # ── 기본 가중치 ──────────────────────────────────────────────────────────
    def get_base_weights(self) -> dict:
        return self.base_weights

    def update_weights(self, period: str, new_weights: dict):
        target = self.get_base_weights()
        if period in target:
            target[period].update(new_weights)

    # ── 종목+기간 가중치 ─────────────────────────────────────────────────────
    def get_ticker_period_weights(self, ticker: str, period_label: str) -> dict:
        """
        종목+기간별 저장된 가중치를 반환.
        없으면 기간별 기본 가중치 반환.
        """
        days = period_label_to_days(period_label)
        default = self.base_weights.get(period_label, _default_weights_for_days(days))
        return self._ticker_weights.get(ticker, {}).get(period_label, default).copy()

    def update_ticker_period_weights(self, ticker: str, period_label: str, new_weights: dict):
        """종목+기간 가중치 업데이트 (AI 옵티마이저 호출용)"""
        if ticker not in self._ticker_weights:
            self._ticker_weights[ticker] = {}
        existing = self.get_ticker_period_weights(ticker, period_label)
        existing.update(new_weights)
        self._ticker_weights[ticker][period_label] = existing

    def get_all_ticker_weights(self) -> dict:
        return self._ticker_weights

    # ── 머신러닝 가중치 저장/로드 ─────────────────────────────────────────────────────────────

    def save_ticker_weights(self, filepath=None):
        filepath = filepath or self.TICKER_WEIGHT_FILE
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._ticker_weights, f, indent=2, ensure_ascii=False)
        print(f"[Config] 종목별 가중치 저장 → {filepath}")

    def load_ticker_weights(self, filepath=None) -> bool:
        filepath = filepath or self.TICKER_WEIGHT_FILE
        if not os.path.exists(filepath):
            return False
        with open(filepath, 'r', encoding='utf-8') as f:
            self._ticker_weights = json.load(f)
        print(f"[Config] 종목별 가중치 로드 ✓ ({len(self._ticker_weights)} 종목)")
        return True
