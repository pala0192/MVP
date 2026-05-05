import json
import os

class Config:
    def __init__(self):
        # 투자 모드 (단기/중기/장기 또는 자동 'AUTO')
        self.investment_mode = 'AUTO'
        self.initial_capital = 10000000  # 1천만원
        
        # 보조지표별 기본 가중치 템플릿
        default_short_weights = {
            'rsi': 0.3,
            'stoch': 0.3,
            'bollinger': 0.2,
            'macd': 0.2
        }
        default_mid_weights = {
            'macd': 0.4,
            'ema20': 0.3,
            'rsi': 0.2,
            'bollinger': 0.1
        }
        default_long_weights = {
            'ema60': 0.4,
            'ema120': 0.2,
            'macd': 0.2,
            'atr': 0.2
        }

        # 시장별(미국/한국) 가중치 분리
        self.us_weights = {
            'short': default_short_weights.copy(),
            'mid': default_mid_weights.copy(),
            'long': default_long_weights.copy()
        }
        
        self.kr_weights = {
            'short': default_short_weights.copy(),
            'mid': default_mid_weights.copy(),
            'long': default_long_weights.copy()
        }
        
    def get_market_weights(self, market):
        """특정 시장의 전체 가중치(short, mid, long) 반환"""
        if market.upper() == 'US':
            return self.us_weights
        elif market.upper() == 'KR':
            return self.kr_weights
        else:
            raise ValueError(f"Unknown market: {market}")

    def update_weights(self, market, period, new_weights):
        """AI 옵티마이저가 특정 시장과 기간의 가중치를 업데이트할 때 사용"""
        target_weights = self.get_market_weights(market)
        if period in target_weights:
            target_weights[period].update(new_weights)

    def save_to_file(self, filepath='config_weights.json'):
        """학습된 시장별 가중치를 JSON 파일로 저장합니다."""
        data = {
            'US': self.us_weights,
            'KR': self.kr_weights
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
    def load_from_file(self, filepath='config_weights.json'):
        """저장된 가중치 JSON 파일을 불러옵니다."""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 기존 레거시 포맷 호환성 지원 (US와 KR 구분 없이 short_weights 등이 바로 있는 경우)
                if 'short_weights' in data or 'mid_weights' in data or 'long_weights' in data:
                    print("[Config] 구버전 가중치 파일 감지. US 및 KR 시장의 초기값으로 복사하여 마이그레이션합니다.")
                    legacy_short = data.get('short_weights', self.us_weights['short'])
                    legacy_mid = data.get('mid_weights', self.us_weights['mid'])
                    legacy_long = data.get('long_weights', self.us_weights['long'])
                    
                    self.us_weights['short'].update(legacy_short)
                    self.us_weights['mid'].update(legacy_mid)
                    self.us_weights['long'].update(legacy_long)
                    
                    self.kr_weights['short'].update(legacy_short)
                    self.kr_weights['mid'].update(legacy_mid)
                    self.kr_weights['long'].update(legacy_long)
                    return True

                # 새로운 포맷 로드
                if 'US' in data:
                    for period in ['short', 'mid', 'long']:
                        self.us_weights[period].update(data['US'].get(period, {}))
                
                if 'KR' in data:
                    for period in ['short', 'mid', 'long']:
                        self.kr_weights[period].update(data['KR'].get(period, {}))
                        
            return True
        return False
