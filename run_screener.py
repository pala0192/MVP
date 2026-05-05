import argparse
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from tickers import get_top_tickers
from screener import StockScreener

def main():
    print("=========================================")
    print("      📈 주식 검색기 (Stock Screener)     ")
    print("=========================================")
    
    try:
        print("1. 미국 주식 (S&P 500 Top 150)")
        print("2. 한국 주식 (KRX Top 150)")
        market_choice = input("검색할 시장을 선택하세요 [1/2] (기본값: 1): ").strip()
        market_choice = market_choice if market_choice else '1'
        
        country = 'US' if market_choice == '1' else 'KR'
        print(f"\n[{country}] 대표 150개 종목 리스트를 불러오는 중...")
        tickers = get_top_tickers(country, 150)
        
        print("\n[검색 조건 설정]")
        period = input("목표 기간을 선택하세요 [short/mid/long] (기본값: short): ").strip().lower()
        period = period if period in ['short', 'mid', 'long'] else 'short'
        
        trend = input("예상 방향을 선택하세요 [up/down] (기본값: up): ").strip().lower()
        trend = trend if trend in ['up', 'down'] else 'up'
        
        vol_input = input("최소 거래량을 입력하세요 (기본값: 100000): ").strip()
        min_vol = int(vol_input) if vol_input else 100000
        
        val_input = input("최소 거래대금을 입력하세요 (기본값: 0): ").strip()
        min_val = float(val_input) if val_input else 0.0
        
        screener = StockScreener(tickers)
        screener.run(period_mode=period, trend_mode=trend, min_volume=min_vol, min_value=min_val)
        
    except KeyboardInterrupt:
        print("\n\n검색을 중단합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
