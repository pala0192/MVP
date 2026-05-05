import yfinance as yf
import FinanceDataReader as fdr

print("--- Testing FinanceDataReader KRX ---")
try:
    df_krx = fdr.StockListing('KRX')
    print(f"KRX Count: {len(df_krx)}")
    print(df_krx.head())
except Exception as e:
    print(f"FDR Error: {e}")

print("\n--- Testing yfinance 005930.KS ---")
try:
    ticker = "005930.KS"
    df = yf.download(ticker, period="1mo")
    print(f"Data for {ticker}:")
    print(df.tail())
except Exception as e:
    print(f"yfinance Error: {e}")
