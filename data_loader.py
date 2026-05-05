import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import random
import FinanceDataReader as fdr

class TickerSelector:
    _cache = {}

    @classmethod
    def get_random_ticker(cls, market='US'):
        market = market.upper()
        if market not in cls._cache:
            print(f"[{market}] 시장 종목 리스트를 불러옵니다 (이후부터는 캐시 사용)...")
            if market == 'KR':
                df = fdr.StockListing('KRX')
                if 'Marcap' in df.columns:
                    df = df.sort_values('Marcap', ascending=False)
                
                tickers = []
                for _, row in df.iterrows():
                    code = str(row['Code']).strip()
                    mkt = str(row.get('Market', '')).upper()
                    if 'KOSPI' in mkt:
                        tickers.append(code + '.KS')
                    elif 'KOSDAQ' in mkt:
                        tickers.append(code + '.KQ')
                    else:
                        tickers.append(code + '.KS')
                cls._cache['KR'] = tickers
                
            elif market == 'US':
                # NASDAQ은 시가총액이 큰 기업부터 정렬되어 내려오는 경향이 있습니다.
                df = fdr.StockListing('NASDAQ')
                cls._cache['US'] = df['Symbol'].tolist()
            else:
                raise ValueError(f"지원하지 않는 시장입니다: {market}")

        tickers = cls._cache[market]
        
        # 85% 확률로 상위 200개 종목 내에서, 15% 확률로 나머지 종목 내에서 추출
        if random.random() < 0.85:
            top_n = min(200, len(tickers))
            return random.choice(tickers[:top_n])
        else:
            if len(tickers) > 200:
                return random.choice(tickers[200:])
            else:
                return random.choice(tickers)


class MarketDataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        
    def fetch_data(self, months_ago_start, months_ago_end=0):
        """
        months_ago_start: 데이터 수집 시작 시점 (N+6개월 등)
        months_ago_end: 데이터 수집 종료 시점 (N개월 등. 0이면 현재)
        """
        end_date = datetime.now() - timedelta(days=30 * months_ago_end)
        start_date = end_date - timedelta(days=30 * months_ago_start)
        
        print(f"[{self.ticker}] Data fetch: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        df = yf.download(self.ticker, start=start_date, end=end_date, progress=False)
        if df.empty:
            raise ValueError(f"No data found for {self.ticker}")
        
        # MultiIndex columns 처리 (yfinance 최신 버전 호환성)
        if isinstance(df.columns, pd.MultiIndex):
            # level 1 이 ticker 인 경우 제거
            df.columns = df.columns.droplevel(1)
            
        df.dropna(inplace=True)
        return df
