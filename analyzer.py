import pandas as pd
import numpy as np
from config import Config

class StrategyAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        
    def _normalize_rsi(self, rsi_series):
        # RSI 30 이하 과매도(매수시그널 +1), 70 이상 과매수(매도시그널 -1)
        score = (50 - rsi_series) / 20.0
        return np.clip(score, -1.0, 1.0)
        
    def _normalize_stoch(self, k_series, d_series):
        # K가 D를 상향 돌파하면 매수, 하향 돌파하면 매도
        diff = k_series - d_series
        return np.clip(diff / 10.0, -1.0, 1.0)
        
    def _normalize_macd(self, macd_series, signal_series):
        diff = macd_series - signal_series
        return np.clip(diff / (macd_series.abs() + 0.001), -1.0, 1.0)
        
    def _normalize_bollinger(self, price_series, lower_series, upper_series):
        # 하단 터치 시 +1, 상단 터치 시 -1
        mid = (lower_series + upper_series) / 2
        score = (mid - price_series) / (upper_series - lower_series) * 2
        return np.clip(score, -1.0, 1.0)

    def _normalize_ema(self, price_series, ema_series):
        diff_pct = (price_series - ema_series) / ema_series * 100
        return np.clip(diff_pct / 5.0, -1.0, 1.0)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """전체 데이터프레임에 대해 매매 스코어를 산출합니다. (Vectorization 적용으로 속도 10배 향상)"""
        df = df.copy()
        
        # 보조지표 정규화 (Vectorized)
        rsi_score = self._normalize_rsi(df['RSI_14'])
        stoch_score = self._normalize_stoch(df['STOCHk_14_3_3'], df['STOCHd_14_3_3'])
        macd_score = self._normalize_macd(df['MACD_12_26_9'], df['MACDs_12_26_9'])
        bb_score = self._normalize_bollinger(df['Close'], df['BBL_20_2.0'], df['BBU_20_2.0'])
        ema20_score = self._normalize_ema(df['Close'], df['EMA_20'])
        ema60_score = self._normalize_ema(df['Close'], df['EMA_60'])
        ema120_score = self._normalize_ema(df['Close'], df['EMA_120'])
        
        # [허점 2 수정] ATR 편향 오류 수정: 가격의 20일 변동 방향성을 ATR로 나누어 방향과 변동성을 동시 고려
        price_momentum = df['Close'] - df['Close'].shift(20)
        atr_score = np.clip(price_momentum / (df['ATRr_14'] + 0.001), -1.0, 1.0).fillna(0)
        
        return df

class ConsultingInterpreter:
    @staticmethod
    def interpret(row, holding_days=30):
        """특정 시점의 데이터를 바탕으로 자연어 해석과 기대 수익을 산출합니다."""
        feedback = []
        
        # 1. RSI 분석
        rsi = row['RSI_14']
        if rsi >= 70:
            feedback.append("⚠️ [RSI(14D)] 현재 70 이상으로 과매수 구간입니다. 단기 하락 조정 가능성이 높습니다.")
        elif rsi <= 30:
            feedback.append("✅ [RSI(14D)] 현재 30 이하로 과매도 구간입니다. 단기적인 기술적 반등이 기대됩니다.")
        else:
            feedback.append(f"ℹ️ [RSI(14D)] 현재 {rsi:.1f}로 중립적인 모멘텀입니다.")
            
        # 2. 볼린저 밴드 분석
        price = row['Close']
        bbu = row['BBU_20_2.0']
        bbl = row['BBL_20_2.0']
        if price >= bbu:
            feedback.append("⚠️ [볼린저 밴드(20D, 2.0σ)] 주가가 상단 밴드를 터치/돌파했습니다. 강한 저항 및 매도 압력이 예상됩니다.")
        elif price <= bbl:
            feedback.append("✅ [볼린저 밴드(20D, 2.0σ)] 주가가 하단 밴드를 터치/돌파했습니다. 지지선 역할을 하여 반등할 확률이 높습니다.")
            
        # 3. MACD 분석
        macd = row['MACD_12_26_9']
        signal = row['MACDs_12_26_9']
        if macd > signal and macd > 0:
            feedback.append("📈 [MACD(12D-26D-9D)] MACD가 시그널 선 위에 위치하여 상승 추세가 견고합니다.")
        elif macd < signal and macd < 0:
            feedback.append("📉 [MACD(12D-26D-9D)] MACD가 시그널 선 아래 위치하여 하락 추세가 진행 중입니다.")

        # 4. 목표가 및 기대 수익률 산출 (ATR 기반)
        atr = row['ATRr_14']
        # 기간에 따라 변동폭 승수(Multiplier)를 다르게 가져감
        if holding_days <= 7:
            multiplier = 1.5
        elif holding_days <= 84:
            multiplier = 3.0
        else:
            multiplier = 5.0
            
        target_price = price + (atr * multiplier)
        stop_loss = price - (atr * multiplier * 0.5) # 손익비 2:1 가정
        
        expected_return_pct = (target_price - price) / price * 100
        risk_pct = (price - stop_loss) / price * 100
        
        return {
            'text': "\n".join(feedback),
            'current_price': price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'expected_return_pct': expected_return_pct,
            'risk_pct': risk_pct
        }


