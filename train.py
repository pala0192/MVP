# 학습용 파일
import sys
import random
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from config import Config
from data_loader import MarketDataLoader, TickerSelector
from indicators import IndicatorEngine
from optimizer import WeightOptimizer

def run_training(num_tickers=50, epochs=5):
    print(f"=== [자동 학습 모드] 총 {num_tickers}개 종목에 대한 연속 최적화 시작 ===")
    
    config = Config()
    
    # 이전에 학습된 가중치가 있다면 불러와서 그 지점부터 학습을 이어나갑니다 (Continuous Learning)
    if config.load_from_file():
        print("[0] 기존에 학습된 가중치(config_weights.json)를 불러와 이어서 학습합니다.")
    else:
        print("[0] 저장된 가중치가 없어 기본값에서 학습을 시작합니다.")
        
    for i in range(1, num_tickers + 1):
        market = random.choice(['US', 'KR'])
        ticker = TickerSelector.get_random_ticker(market)
        
        print(f"\n{'='*50}")
        print(f"[{i}/{num_tickers}] 시장: {market} | 자동 선택된 종목: {ticker} (데이터 수집 중...)")
        print(f"{'='*50}")
        
        data_loader = MarketDataLoader(ticker)
        
        try:
            # 예: 과거 24개월 전부터 6개월 전까지의 데이터를 순수 Train으로만 사용
            train_df = data_loader.fetch_data(months_ago_start=24, months_ago_end=6)
            train_df = IndicatorEngine.calculate_all(train_df)
            
            print(f"[{i}/{num_tickers}] 가중치 최적화 학습 중 ({ticker} 단/중/장기 모델)...")
            optimizer = WeightOptimizer(config, train_df, None) 
            
            for mode in ['short', 'mid', 'long']:
                optimizer.train(market=market, period_mode=mode, epochs=epochs)
        except Exception as e:
            print(f"[{ticker}] 데이터 부족 또는 학습 중 오류 발생, 다음 종목으로 넘어갑니다: {e}")
            continue
            
        # 1개 종목 학습이 끝날 때마다 중간 저장
        config.save_to_file()
        print(f"[{i}/{num_tickers}] {ticker} 학습 결과를 config_weights.json에 임시 저장했습니다.")
        
        time.sleep(1) # 연속 요청 방지
        
    print("\n=== 모든 종목 학습 완료! 최종 가중치가 저장되었습니다. ===")

if __name__ == "__main__":
    run_training(num_tickers=50, epochs=5)
