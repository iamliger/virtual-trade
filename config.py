# config.py
import logging

# [시스템 언어 설정]
SYSTEM_LANGUAGE = (
    "Korean"  # "Korean"으로 설정 시 모든 AI 응답 및 리포트가 한글로 고정됨
)

# [매매 설정]
DEFAULT_SEED_MONEY = 100000  # 초기 자본금 (10만원)
DEFAULT_GOAL_PROFIT = 5000  # 목표 수익 (5천원)
TRADE_RATIO = 0.9  # 한 종목에 투입할 자산 비율
SCAN_INTERVAL = 60  # 시장 스캔 주기 (60초)

# [AI 설정]
AI_MODEL = "llama3"
AI_TEMPERATURE = 0.05

# [로깅 설정]
LOG_FILE = "app.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# [네트워크 설정]
TIMEOUT = 10
RETRY_COUNT = 3
