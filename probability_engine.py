"""
probability_engine.py - 다층 신호 통합 → 실현가능성% + 매수/매도 수치 (-1~+1)
"""
import numpy as np
from typing import Optional


class ProbabilityEngine:
    """
    입력: 기술지표 점수, 뉴스 감성 점수, 옵션 확률, 목표 수익률, 홀딩 기간
    출력: feasibility_pct (0~100), buy_sell_score (-1~+1)
    
    기간별 가중치:
      단기(≤30일):  뉴스 30% / 기술지표 40% / 보조지표 25% / 옵션  5%
      중기(≤180일): 뉴스 25% / 기술지표 30% / 보조지표 25% / 옵션 20%
      장기(>180일): 뉴스 15% / 기술지표 15% / 보조지표 20% / 옵션 50%
    """

    @staticmethod
    def get_time_weights(holding_days: int) -> dict:
        if holding_days <= 30:
            return {'news': 0.30, 'technical': 0.40, 'indicator': 0.25, 'options': 0.05}
        elif holding_days <= 180:
            return {'news': 0.25, 'technical': 0.30, 'indicator': 0.25, 'options': 0.20}
        else:
            return {'news': 0.15, 'technical': 0.15, 'indicator': 0.20, 'options': 0.50}

    @staticmethod
    def sigmoid(x: float, scale: float = 2.5) -> float:
        return 1.0 / (1.0 + np.exp(-x * scale))



    @staticmethod
    def apply_ticker_weights(latest_row, ticker_weights: dict) -> float:
        """머신러닝 최적화 가중치를 최신 데이터에 적용하여 정밀 스코어 산출"""
        def norm_clip(val):
            return float(np.clip(val, -1.0, 1.0))

        # 기본 점수 환산
        rsi_val = float(latest_row.get('RSI_14', 50))
        stoch_k = float(latest_row.get('STOCHk_14_3_3', 50))
        stoch_d = float(latest_row.get('STOCHd_14_3_3', 50))
        macd = float(latest_row.get('MACD_12_26_9', 0))
        macds = float(latest_row.get('MACDs_12_26_9', 0))
        close = float(latest_row.get('Close', 1))
        bbu = float(latest_row.get('BBU_20_2.0', 1))
        bbl = float(latest_row.get('BBL_20_2.0', 1))
        ema20 = float(latest_row.get('EMA_20', close))
        ema60 = float(latest_row.get('EMA_60', close))
        ema120 = float(latest_row.get('EMA_120', close))
        
        rsi_score = norm_clip((50 - rsi_val) / 20.0)
        stoch_score = norm_clip((stoch_k - stoch_d) / 10.0)
        macd_score = norm_clip((macd - macds) / (abs(macd) + 0.001))
        mid = (bbu + bbl) / 2.0
        bb_score = norm_clip((mid - close) / (bbu - bbl + 0.001) * 2)
        ema20_score = norm_clip(((close - ema20) / ema20 * 100) / 5.0)
        ema60_score = norm_clip(((close - ema60) / ema60 * 100) / 5.0)
        ema120_score = norm_clip(((close - ema120) / ema120 * 100) / 5.0)
        
        # 가중치 합산
        total = sum(ticker_weights.values()) or 1.0
        signal = (
            rsi_score * ticker_weights.get('rsi', 0) +
            stoch_score * ticker_weights.get('stoch', 0) +
            macd_score * ticker_weights.get('macd', 0) +
            bb_score * ticker_weights.get('bollinger', 0) +
            ema20_score * ticker_weights.get('ema20', 0) +
            ema60_score * ticker_weights.get('ema60', 0) +
            ema120_score * ticker_weights.get('ema120', 0)
        )
        return norm_clip(signal / total)

    @classmethod
    def compute(
        cls,
        technical_score: float,
        news_score: float,
        indicator_score: float,
        options_probability,
        target_return_pct: float,
        holding_days: float,
        hist_vol_probability=None,
        ticker_weights: dict = None,   # 종목+기간별 저장 가중치
    ) -> dict:
        """
        최종 분석 계산.
        ticker_weights: 종목+기간 전용 신호 가중치 (없으면 기간별 기본값 사용)
        """
        weights = cls.get_time_weights(holding_days)

        # ticker_weights가 있으면 기술 지표(차트/보조지표) 가중치를 조정
        if ticker_weights:
            # 기술 지표 비중을 높여 최적화 결과가 강하게 반영되도록 함
            weights['technical'] = 0.50
            weights['indicator'] = 0.20
            # 옵션 비중 축소, 뉴스 비중 유지
            pass

        # 옵션 점수 (-1~+1 변환)
        if options_probability is not None:
            options_score = (options_probability - 0.5) * 2.0
        elif hist_vol_probability is not None:
            # 한국주식: HV 기반 확률을 옵션 점수 대용
            options_score = (hist_vol_probability - 0.5) * 2.0
        else:
            # 옵션 데이터 없으면 기술지표에 가중치 이전
            options_score = 0.0
            weights['indicator'] += weights['options']
            weights['options'] = 0.0

        # 가중 종합 매수/매도 점수
        buy_sell_score = (
            news_score      * weights['news'] +
            technical_score * weights['technical'] +
            indicator_score * weights['indicator'] +
            options_score   * weights['options']
        )
        buy_sell_score = float(np.clip(buy_sell_score, -1.0, 1.0))

        # 방향 정렬: 목표 수익률이 양수면 매수 방향 점수를 확률로
        if target_return_pct >= 0:
            direction_score = buy_sell_score
        else:
            direction_score = -buy_sell_score

        # sigmoid → 확률 (%)
        base_prob = cls.sigmoid(direction_score) * 100.0

        # 역사적 변동성 확률과 블렌딩
        if hist_vol_probability is not None:
            hv_prob_pct = hist_vol_probability * 100.0
            # 모델 신호 50% + 통계적 확률 50%
            feasibility_pct = 0.5 * base_prob + 0.5 * hv_prob_pct
        else:
            feasibility_pct = base_prob

        feasibility_pct = float(np.clip(feasibility_pct, 1.0, 99.0))

        # 기간 레이블
        if holding_days <= 30:
            period_label = f"단기 ({holding_days}일)"
        elif holding_days <= 180:
            period_label = f"중기 ({holding_days}일)"
        else:
            period_label = f"장기 ({holding_days}일)"

        return {
            'feasibility_pct': round(feasibility_pct, 1),
            'buy_sell_score': round(buy_sell_score, 3),
            'weights_used': weights,
            'breakdown': {
                'news': round(news_score, 3),
                'technical': round(technical_score, 3),
                'indicator': round(indicator_score, 3),
                'options': round(options_score, 3),
            },
            'holding_period': period_label,
        }
