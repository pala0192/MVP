import pandas as pd

class BacktestSimulator:
    def __init__(self, initial_capital=10000000):
        self.initial_capital = initial_capital
        
    def run(self, df: pd.DataFrame, period_mode='short', threshold=0.3):
        """
        간단한 백테스트 시뮬레이션
        period_mode: 'short', 'mid', 'long' 중 하나
        threshold: 매수/매도 시그널 임계값
        """
        capital = self.initial_capital
        position = 0
        history = []
        
        score_col = f'Score_{period_mode.capitalize()}'
        
        for index, row in df.iterrows():
            price = row['Close']
            score = row[score_col]
            
            # 매수 시그널
            if score > threshold and capital >= price:
                shares_to_buy = int(capital // price)
                if shares_to_buy > 0:
                    capital -= shares_to_buy * price
                    position += shares_to_buy
                    history.append({'date': index, 'action': 'BUY', 'price': price, 'shares': shares_to_buy})
                    
            # 매도 시그널
            elif score < -threshold and position > 0:
                capital += position * price
                history.append({'date': index, 'action': 'SELL', 'price': price, 'shares': position})
                position = 0
                
        # 최종 자산 가치 계산
        final_value = capital + (position * df.iloc[-1]['Close'])
        return_pct = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return {
            'final_value': final_value,
            'return_pct': return_pct,
            'trade_history': history
        }
