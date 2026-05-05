import FinanceDataReader as fdr
df = fdr.StockListing('KRX')
print(f"Columns: {df.columns.tolist()}")
print(df[['Code', 'Name', 'Market']].head())
