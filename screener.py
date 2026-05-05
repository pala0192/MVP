import pandas as pd
from data_loader import MarketDataLoader
from indicators import IndicatorEngine
from analyzer import ScreenerCondition, ScreenerInterpreter
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class StockScreener:
    def __init__(self, tickers: list):
        self.tickers = tickers
        
    def run(self, period_mode: str, trend_mode: str, min_volume: int = 0, min_value: float = 0):
        print(f"\n🚀 [Stock Screener] 시작합니다...")
        print(f" - 대상 종목수: {len(self.tickers)}개")
        print(f" - 조건: {period_mode} / {trend_mode}")
        print(f" - 필터: 최소 거래량 {min_volume:,.0f}, 최소 거래대금 {min_value:,.0f}")
        print("="*60)
        
        matched_tickers = []
        
        from tqdm import tqdm
        
        for ticker in tqdm(self.tickers, desc="검색 진행률", unit="종목"):
            
            try:
                # EMA_120 계산 워밍업을 위해 18개월치를 수집하고, 지표 계산 후 최근 6개월만 사용
                loader = MarketDataLoader(ticker)
                
                # yfinance 진행바 숨김 처리를 위해 조용히 다운로드
                import contextlib, io
                from datetime import datetime, timedelta
                with contextlib.redirect_stdout(io.StringIO()):
                    raw_df = loader.fetch_data(months_ago_start=18, months_ago_end=0)
                
                if len(raw_df) < 120:
                    continue  # raw 데이터 자체가 부족
                    
                # 보조지표 계산 (dropna 후 EMA_120 유효 구간만 남음)
                full_df = IndicatorEngine.calculate_all(raw_df)
                
                # 최근 6개월치만 슬라이싱하여 스크리닝 조건 검사
                cutoff = datetime.now() - timedelta(days=30 * 6)
                df = full_df[full_df.index >= cutoff]
                if len(df) < 2:
                    continue  # 유효 데이터 부족
                
                # 조건 검사 (환율 보정을 위해 ticker 전달)
                is_match, result_data = ScreenerCondition.check_conditions(
                    ticker, df, period_mode, trend_mode, min_volume, min_value
                )
                
                if is_match:
                    matched_tickers.append((ticker, result_data))
            except Exception as e:
                # 특정 종목에서 에러가 나면 그냥 패스 (상장폐지 등)
                continue
                
        print("\n\n" + "="*60)
        print(f"✅ 검색 완료! 총 {len(matched_tickers)}개의 종목이 조건을 만족했습니다.")
        print("="*60 + "\n")
        
        from tickers import get_ticker_name
        for ticker, result_data in matched_tickers:
            stock_name = get_ticker_name(ticker)
            report = ScreenerInterpreter.generate_report(ticker, result_data, period_mode, trend_mode, stock_name=stock_name)
            print(report)
            
        return matched_tickers
