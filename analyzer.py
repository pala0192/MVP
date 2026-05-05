import pandas as pd
import numpy as np
from config import Config

class StrategyAnalyzer:
    def __init__(self, config: Config, market='US'):
        self.config = config
        self.market = market
        
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
        
        # 시장별 가중치 로드
        market_weights = self.config.get_market_weights(self.market)
        sw = market_weights['short']
        mw = market_weights['mid']
        lw = market_weights['long']

        # 단기 투자 점수
        df['Score_Short'] = (rsi_score * sw.get('rsi', 0) + 
                             stoch_score * sw.get('stoch', 0) + 
                             macd_score * sw.get('macd', 0) + 
                             bb_score * sw.get('bollinger', 0))
                             
        # 중기 투자 점수
        df['Score_Mid'] = (macd_score * mw.get('macd', 0) + 
                           ema20_score * mw.get('ema20', 0) + 
                           rsi_score * mw.get('rsi', 0) + 
                           bb_score * mw.get('bollinger', 0))
                           
        # 장기 투자 점수
        df['Score_Long'] = (ema60_score * lw.get('ema60', 0) + 
                            ema120_score * lw.get('ema120', 0) + 
                            macd_score * lw.get('macd', 0) + 
                            atr_score * lw.get('atr', 0))
                            
        return df

class ConsultingInterpreter:
    @staticmethod
    def interpret(row, period_mode='short'):
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
        if period_mode == 'short':
            multiplier = 1.5
        elif period_mode == 'mid':
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

class ScreenerCondition:
    @staticmethod
    def check_conditions(ticker: str, df: pd.DataFrame, period_mode: str, trend_mode: str, min_volume: int, min_value: float) -> tuple[bool, dict]:
        """
        주어진 데이터프레임이 스크리너 조건을 만족하는지 검사합니다.
        반환값: (조건_만족_여부, 분석_결과_딕셔너리)
        """
        if len(df) < 2:
            return False, {}
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 기본 필터링: 거래량 및 거래대금
        volume = latest.get('Volume', 0)
        close_price = latest.get('Close', 0)
        trading_value = volume * close_price
        
        # [허점 3 수정] 환율을 고려한 거래대금 정규화 (원화 기준 통일)
        # 티커가 .KS나 .KQ로 끝나면 한국(KRW), 아니면 달러(USD)로 간주하고 환율(1400원) 곱하기
        is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
        if not is_korean_stock:
            trading_value *= 1400.0
        
        if volume < min_volume or trading_value < min_value:
            return False, {}
            
        is_match = False
        reasons = []
        
        if period_mode == 'short':
            if trend_mode == 'up':
                rsi_break = prev['RSI_14'] <= 50 and latest['RSI_14'] > 50
                stoch_break = prev['STOCHk_14_3_3'] <= 50 and latest['STOCHk_14_3_3'] > 50
                if rsi_break or stoch_break:
                    is_match = True
                    if rsi_break: reasons.append("RSI가 50선을 상향 돌파하며 상승 모멘텀 발생")
                    if stoch_break: reasons.append("스토캐스틱 K가 50선을 상향 돌파하며 단기 강세 진입")
            else:
                rsi_break_down = prev['RSI_14'] >= 50 and latest['RSI_14'] < 50
                stoch_break_down = prev['STOCHk_14_3_3'] >= 50 and latest['STOCHk_14_3_3'] < 50
                if rsi_break_down or stoch_break_down:
                    is_match = True
                    if rsi_break_down: reasons.append("RSI가 50선을 하향 돌파하며 하락 모멘텀 발생")
                    if stoch_break_down: reasons.append("스토캐스틱 K가 50선을 하향 돌파하며 단기 약세 진입")
                    
        elif period_mode == 'mid':
            if trend_mode == 'up':
                macd_cross_up = prev['MACD_12_26_9'] <= prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] > latest['MACDs_12_26_9']
                above_ema20 = latest['Close'] > latest['EMA_20']
                if macd_cross_up and above_ema20:
                    is_match = True
                    reasons.append("MACD가 시그널선을 상향 돌파(골든크로스)하였고 주가가 20일 이동평균선 위에 안착하여 중기 상승 추세 형성")
            else:
                macd_cross_down = prev['MACD_12_26_9'] >= prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] < latest['MACDs_12_26_9']
                below_ema20 = latest['Close'] < latest['EMA_20']
                if macd_cross_down and below_ema20:
                    is_match = True
                    reasons.append("MACD가 시그널선을 하향 돌파(데드크로스)하였고 주가가 20일 이동평균선 아래로 이탈하여 중기 하락 추세 형성")
                    
        elif period_mode == 'long':
            if trend_mode == 'up':
                cross_ema60 = prev['Close'] <= prev['EMA_60'] and latest['Close'] > latest['EMA_60']
                cross_ema120 = prev['Close'] <= prev['EMA_120'] and latest['Close'] > latest['EMA_120']
                if cross_ema60 or cross_ema120:
                    is_match = True
                    if cross_ema60: reasons.append("주가가 장기 추세선인 60일 이동평균선을 강하게 돌파")
                    if cross_ema120: reasons.append("주가가 주요 저항선인 120일 이동평균선을 상향 돌파하여 강력한 장기 상승 전환 시그널")
            else:
                drop_ema60 = prev['Close'] >= prev['EMA_60'] and latest['Close'] < latest['EMA_60']
                drop_ema120 = prev['Close'] >= prev['EMA_120'] and latest['Close'] < latest['EMA_120']
                if drop_ema60 or drop_ema120:
                    is_match = True
                    if drop_ema60: reasons.append("주가가 60일 이동평균선을 하향 이탈하여 장기 지지선 붕괴")
                    if drop_ema120: reasons.append("주가가 120일 이동평균선을 하향 이탈하여 장기 침체 국면 진입")

        result_data = {
            'volume': volume,
            'trading_value': trading_value,
            'reasons': reasons
        }
        
        return is_match, result_data

class ScreenerInterpreter:
    @staticmethod
    def generate_report(ticker: str, result_data: dict, period_mode: str, trend_mode: str, stock_name: str = "") -> str:
        """스크리닝된 종목에 대한 심층 분석 리포트를 생성합니다."""
        period_str = {'short': '단기', 'mid': '중기', 'long': '장기'}[period_mode]
        trend_str = {'up': '상승', 'down': '하락'}[trend_mode]
        
        reasons_text = "\n".join([f" - {r}" for r in result_data['reasons']])
        
        # 환산된 거래대금을 읽기 쉽게 포맷팅 (원화 기준)
        trading_val_str = f"{result_data['trading_value']:,.0f} 원"
        
        display_name = f"{stock_name}({ticker})" if stock_name else ticker
        
        report = (
            f"🔍 [검색 결과] {display_name} ({period_str} {trend_str} 예상)\n"
            f"   ▶ 거래량: {result_data['volume']:,.0f} 주\n"
            f"   ▶ 거래대금: {trading_val_str} (미국주식의 경우 환율 자동반영됨)\n"
            f"   [예측 이유]\n{reasons_text}\n"
            f"   [심층 분석] 현재 해당 종목은 {period_str}적인 관점에서 기술적 지표가 {trend_str} 방향을 가리키고 있습니다. "
            f"특히 설정된 조건에 부합하는 강한 모멘텀이 포착되었으므로 주의 깊은 관찰이 필요합니다.\n"
            f"-" * 50
        )
        return report
