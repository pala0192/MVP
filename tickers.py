import FinanceDataReader as fdr

def get_top_tickers(country='US', top_n=150):
    """
    country: 'US' 또는 'KR'
    top_n: 가져올 종목 개수
    """
    if country == 'US':
        try:
            # S&P500 종목을 가져옴
            df = fdr.StockListing('S&P500')
            return df['Symbol'].head(top_n).tolist()
        except Exception as e:
            print(f"Failed to fetch US tickers: {e}")
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'] # Fallback
            
    elif country == 'KR':
        try:
            # 한국 전체 시장 종목을 가져옴
            df = fdr.StockListing('KRX')
            
            # 시가총액(Marcap) 기준으로 정렬 (있는 경우)
            if 'Marcap' in df.columns:
                df = df.sort_values(by='Marcap', ascending=False)
                
            tickers = []
            for _, row in df.head(top_n).iterrows():
                code = row['Code']
                market = row['Market']
                # yfinance 호환을 위해 KOSPI는 .KS, KOSDAQ은 .KQ를 붙임
                if 'KOSPI' in market:
                    tickers.append(f"{code}.KS")
                elif 'KOSDAQ' in market:
                    tickers.append(f"{code}.KQ")
                else:
                    tickers.append(f"{code}.KS")
            return tickers
        except Exception as e:
            print(f"Failed to fetch KR tickers: {e}")
            return ['005930.KS', '000660.KS', '035420.KS', '035720.KS'] # Fallback
            
_name_cache = {}

def get_ticker_name(ticker):
    """티커 심볼을 받아 종목명을 반환합니다. (캐시 활용)"""
    if ticker in _name_cache:
        return _name_cache[ticker]
        
    try:
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            code = ticker.split('.')[0]
            if 'KRX' not in _name_cache:
                _name_cache['KRX'] = fdr.StockListing('KRX')
            df = _name_cache['KRX']
            name = df[df['Code'] == code]['Name'].values[0]
            _name_cache[ticker] = name
            return name
        else:
            # 미국 주식 (S&P 500 등)
            if 'SP500' not in _name_cache:
                _name_cache['SP500'] = fdr.StockListing('S&P500')
            df = _name_cache['SP500']
            name = df[df['Symbol'] == ticker]['Name'].values[0]
            _name_cache[ticker] = name
            return name
    except:
        return ticker # 실패 시 티커 반환
