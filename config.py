# config.py
import logging

# [시스템 설정]
SYSTEM_LANGUAGE = "Korean"
DEBUG = True

# [매매 설정]
DEFAULT_SEED_MONEY = 100000  # 초기 자본금 10만원
DEFAULT_GOAL_PROFIT = 5000  # 목표 수익 5천원
TRADE_RATIO = 0.9  # 가용 자산의 90% 투입
SCAN_INTERVAL = 60  # 60초 주기 스캔

# [AI 및 네트워크]
AI_MODEL = "llama3"
AI_TEMPERATURE = 0.05
TIMEOUT = 10
RETRY_COUNT = 3

# [로깅]
LOG_FILE = "app.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
