# 배포용 파일
import sys
sys.stdout.reconfigure(encoding='utf-8')

from config import Config
from data_loader import MarketDataLoader
from indicators import IndicatorEngine
from analyzer import StrategyAnalyzer, ConsultingInterpreter
from visualizer import ConsultingReport

from tickers import get_ticker_name

def run_serving(ticker='AAPL', period_mode='short'):
    stock_name = get_ticker_name(ticker)
    print(f"=== [서비스 배포 모드] {stock_name}({ticker}) 실시간 분석 컨설팅 ===")
    
    config = Config()
    
    # 1. AI 학습 가중치 로드 (더 이상 여기서 무거운 학습을 하지 않습니다)
    if config.load_from_file():
        print("[1] 사전에 학습된 최적의 가중치(config_weights.json)를 성공적으로 불러왔습니다.")
    else:
        print("[1] ⚠️ 저장된 가중치가 없어 기본 가중치로 진행합니다. (먼저 train.py를 실행하세요)")
        
    # 2. 실전 테스트 데이터 주입 (외부 CSV 또는 최근 실시간 데이터)
    data_loader = MarketDataLoader(ticker)
    print(f"\n[2] {stock_name} 데이터 수집 및 지표 계산...")
    # EMA_120 등 장기 지표 계산을 위해 충분한 워밍업 데이터(18개월)를 가져옵니다.
    # dropna 후에도 최근 6개월치 데이터가 충분히 남도록 넉넉히 수집합니다.
    raw_df = data_loader.fetch_data(months_ago_start=18, months_ago_end=0)
    full_df = IndicatorEngine.calculate_all(raw_df)
    
    # 지표 계산 후, 실제 분석/표시용으로 최근 6개월치만 슬라이싱
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=30 * 6)
    test_df = full_df[full_df.index >= cutoff]
    if len(test_df) == 0:
        test_df = full_df  # 혹시 6개월치도 없으면 전체 사용
    
    # 3. 알고리즘 기반 빠른 컨설팅 산출
    print("\n[3] 가중치 기반 알고리즘 분석 및 자연어 피드백 생성 중...")
    market = 'KR' if ticker.endswith('.KS') or ticker.endswith('.KQ') else 'US'
    analyzer = StrategyAnalyzer(config, market=market)
    analyzed_df = analyzer.generate_signals(test_df)
    
    # 가장 마지막 날(가장 최신 데이터) 기준으로 컨설팅 리포트 작성
    latest_row = analyzed_df.iloc[-1]
    
    print("\n==================================================")
    print(f"📊 {stock_name}({ticker}) 투자 컨설팅 리포트 (기준일: {latest_row.name.strftime('%Y-%m-%d')})")
    print("==================================================")
    
    score_col = f'Score_{period_mode.capitalize()}'
    print(f"📈 {period_mode.upper()} 전략 매매 스코어: {latest_row[score_col]:.2f} (-1.0 매도 ~ +1.0 매수)")
    
    # 자연어 피드백 생성
    interpreter_result = ConsultingInterpreter.interpret(latest_row, period_mode=period_mode)
    print("\n💡 보조지표 종합 해석:")
    print(interpreter_result['text'])
    
    print("\n💰 목표가 및 기대 수익 계산 (ATR 변동성 기반):")
    print(f" - 현재가: {interpreter_result['current_price']:.2f}")
    print(f" - 1차 목표가: {interpreter_result['target_price']:.2f} (기대 수익률: +{interpreter_result['expected_return_pct']:.2f}%)")
    print(f" - 손절가: {interpreter_result['stop_loss']:.2f} (최대 리스크: -{interpreter_result['risk_pct']:.2f}%)")
    print("==================================================")
    
    # 4. 차트 생성
    ConsultingReport.generate_chart(test_df, ticker, stock_name=stock_name)

if __name__ == "__main__":
    # 사용자가 배포 후 실행하는 서비스 로직
    run_serving(ticker='DE', period_mode='short')
