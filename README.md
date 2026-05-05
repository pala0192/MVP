# 📈 AI Quant Trading System

이 프로젝트는 유전 알고리즘(Genetic Algorithm)을 활용하여 주식 보조지표의 최적 가중치를 학습하고, 이를 바탕으로 주식 스크리닝 및 투자 컨설팅 리포트를 제공하는 퀀트 시스템입니다.

## 🌟 주요 기능

1.  **AI 최적화 학습 (`train.py`)**: 유전 알고리즘을 사용하여 과거 데이터에서 가장 높은 수익률을 내는 보조지표(RSI, MACD, Bollinger Bands 등)의 가중치를 자동으로 찾아냅니다. 미국/한국 시장별로 독립적인 가중치를 관리합니다.
2.  **주식 스크리너 (`run_screener.py`)**: 설정한 조건(단기/중기/장기 추세, 거래량, 거래대금 등)에 부합하는 종목을 실시간으로 검색합니다.
3.  **투자 컨설팅 서비스 (`serve.py`)**: 특정 종목에 대해 AI가 학습한 최적 가중치를 적용하여 매매 점수를 산출하고, 자연어 피드백과 함께 목표가/손절가를 포함한 시각화 리포트(HTML)를 생성합니다.

## 🛠 설치 방법 (Installation)

이 프로젝트를 실행하기 위해 Python 3.8 이상이 필요합니다.

1.  저장소를 복제합니다.
    ```bash
    git clone https://github.com/사용자이름/프로젝트이름.git
    cd 프로젝트이름
    ```

2.  가상환경을 생성하고 활성화합니다. (권장)
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  필수 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 사용 방법 (Usage)

### 1. 가중치 학습 (필수 아님, 이미 학습된 파일이 있다면 생략 가능)
AI가 시장 상황을 공부하게 하려면 실행합니다. 학습 결과는 `config_weights.json`에 저장됩니다.
```bash
python train.py
```

### 2. 종목 스크리닝
현재 시장에서 상승/하락 모멘텀이 강한 종목을 찾으려면 실행합니다.
```bash
python run_screener.py
```

### 3. 종목 정밀 분석 및 차트 생성
특정 종목(예: 삼성전자, Apple)의 상세 분석 리포트를 보려면 `serve.py`를 실행합니다. (파일 내 티커 수정 가능)
```bash
python serve.py
```

## 📂 파일 구조

-   `train.py`: 유전 알고리즘 학습 엔진
-   `run_screener.py`: 대화형 주식 검색 도구
-   `serve.py`: 개별 종목 분석 및 서비스 배포용
-   `analyzer.py`: 전략 분석 및 조건 검사 로직
-   `visualizer.py`: Plotly 기반 차트 생성
-   `config.py`: 시스템 설정 및 가중치 관리
-   `data_loader.py`: yfinance 및 FinanceDataReader 데이터 수집

## ⚠️ 면책 조항 (Disclaimer)

이 소프트웨어는 교육 및 연구 목적으로 제작되었습니다. 제공되는 분석 결과와 예상 수익률은 과거 데이터를 기반으로 한 통계적 결과일 뿐이며, 실제 투자 수익을 보장하지 않습니다. 모든 투자의 책임은 투자자 본인에게 있습니다.
