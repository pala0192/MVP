"""
train.py - 5개 지정 종목(Ticker) 대상 가중치 최적화 (머신러닝/랜덤서치)
"""
import os
import random
import numpy as np
import pandas as pd
from datetime import datetime
from config import Config, HOLDING_PERIODS, period_label_to_days
from data_loader import MarketDataLoader
from indicators import IndicatorEngine

def normalize_score(series, method='default'):
    """기본적인 정규화 함수 (analyzer.py와 동일한 로직 적용)"""
    if method == 'rsi':
        return np.clip((50 - series) / 20.0, -1.0, 1.0)
    return np.clip(series, -1.0, 1.0)

def calculate_base_scores(df: pd.DataFrame) -> pd.DataFrame:
    """보조지표들을 -1.0 ~ +1.0 사이의 매수/매도 스코어로 변환합니다."""
    scores = pd.DataFrame(index=df.index)
    
    # RSI (30이하 매수, 70이상 매도)
    scores['rsi'] = np.clip((50 - df['RSI_14']) / 20.0, -1.0, 1.0)
    
    # Stochastic
    scores['stoch'] = np.clip((df['STOCHk_14_3_3'] - df['STOCHd_14_3_3']) / 10.0, -1.0, 1.0)
    
    # MACD
    scores['macd'] = np.clip((df['MACD_12_26_9'] - df['MACDs_12_26_9']) / (df['MACD_12_26_9'].abs() + 0.001), -1.0, 1.0)
    
    # Bollinger Bands
    mid = (df['BBL_20_2.0'] + df['BBU_20_2.0']) / 2
    scores['bollinger'] = np.clip((mid - df['Close']) / (df['BBU_20_2.0'] - df['BBL_20_2.0']) * 2, -1.0, 1.0)
    
    # EMA
    scores['ema20'] = np.clip(((df['Close'] - df['EMA_20']) / df['EMA_20'] * 100) / 5.0, -1.0, 1.0)
    scores['ema60'] = np.clip(((df['Close'] - df['EMA_60']) / df['EMA_60'] * 100) / 5.0, -1.0, 1.0)
    scores['ema120'] = np.clip(((df['Close'] - df['EMA_120']) / df['EMA_120'] * 100) / 5.0, -1.0, 1.0)
    
    # ATR (변동성 모멘텀)
    price_momentum = df['Close'] - df['Close'].shift(20)
    scores['atr'] = np.clip(price_momentum / (df['ATRr_14'] + 0.001), -1.0, 1.0).fillna(0)
    
    return scores

def optimize_ticker_weights(ticker: str, config: Config, iterations: int = 2000):
    """
    특정 종목에 대해 랜덤 서치를 통해 과거 데이터를 바탕으로 
    가장 수익률이 높았던 지표 가중치 조합을 찾습니다.
    """
    print(f"\n🚀 [{ticker}] 머신러닝(랜덤서치) 최적화 시작...")
    
    # 1. 데이터 로드 및 지표 계산 (과거 3년치)
    loader = MarketDataLoader(ticker)
    try:
        raw_df = loader.fetch_data()
        df = IndicatorEngine.calculate_all(raw_df)
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return
        
    scores_df = calculate_base_scores(df)
    features = ['rsi', 'stoch', 'macd', 'bollinger', 'ema20', 'ema60', 'ema120', 'atr']
    
    # 2. 모든 보유 기간에 대해 최적화 진행
    for period_label, days in HOLDING_PERIODS.items():
        shift_days = int(days)
        if shift_days < 1: shift_days = 1
        
        # 미래 수익률 계산
        fwd_return = df['Close'].shift(-shift_days) / df['Close'] - 1.0
        
        valid_idx = fwd_return.dropna().index
        N = len(valid_idx)
        if N < 50:
            continue
            
        # [핵심 로직] 홀딩 기간(days)이 짧을수록 최근 데이터에 기하급수적으로 더 큰 가중치 부여
        decay_factor = min(5.0, max(0.5, 30.0 / shift_days))
        time_weights = np.exp(np.linspace(-decay_factor, 0, N))
        time_weights = time_weights / time_weights.mean()
        time_weights_series = pd.Series(time_weights, index=valid_idx)
            
        test_scores = scores_df.loc[valid_idx]
        test_returns = fwd_return.loc[valid_idx]
        
        best_return = -999.0
        best_weights = None
        
        # 랜덤 서치 진행
        for _ in range(iterations):
            # 랜덤 가중치 생성 및 정규화
            w = {f: random.random() for f in features}
            total = sum(w.values())
            w = {f: val / total for f, val in w.items()}
            
            # 종합 시그널 계산
            combined_signal = sum(test_scores[f] * w[f] for f in features)
            
            # 매수 시그널(>0.2)일 때의 평균 미래 수익률 계산 (최근 데이터 가중)
            buy_mask = combined_signal > 0.2
            if buy_mask.sum() > 0:
                weighted_returns = test_returns[buy_mask] * time_weights_series[buy_mask]
                avg_return = weighted_returns.sum() / time_weights_series[buy_mask].sum()
            else:
                avg_return = -1.0
                
            if avg_return > best_return:
                best_return = avg_return
                best_weights = w
                
        if best_weights:
            # 소수점 3자리 반올림 및 0인 가중치 필터링
            clean_weights = {k: round(v, 3) for k, v in best_weights.items() if round(v, 3) > 0.01}
            config.update_ticker_period_weights(ticker, period_label, clean_weights)
            print(f"  ✓ [{period_label}] 최적화 완료: 기대수익 {best_return*100:.1f}% | 가중치: {clean_weights}")

if __name__ == '__main__':
    from server import KR_WATCHLIST
    
    print("==================================================")
    print(" 🧠 퀀트 가중치 머신러닝(랜덤서치) 최적화 엔진")
    print(" 지정된 5개 종목 및 20개 기간에 대한 학습을 시작합니다.")
    print("==================================================")
    
    config = Config()
    config.load_ticker_weights()
    
    for ticker in KR_WATCHLIST.keys():
        optimize_ticker_weights(ticker, config, iterations=2000)
        
    config.save_ticker_weights()
    print("\n✅ 모든 종목의 최적화 가중치가 ticker_weights.json 에 저장되었습니다!")
    print("서버(server.py)를 재시작하시면 최적화된 AI 가중치가 즉시 반영됩니다.")
