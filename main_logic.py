# main_logic.py (이름 변경 후 코드 전체 교체)
from datetime import datetime  # <--- 여기도 추가해 주세요!

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 설정
TARGET_TICKER = "005930.KS"
TRADE_QUANTITY = 5


def run_trading_cycle(token):
    try:
        stock = yf.Ticker(TARGET_TICKER)
        df = stock.history(period="1d", interval="1m")

        # 뉴스 수집 및 정제
        news_data = stock.news[:3] if stock.news else []
        news_headlines = [item.get("title") for item in news_data if item.get("title")]

        # 💡 [핵심 수정] GUI 표시용 뉴스 문자열을 명확하게 생성
        display_news = (
            "\n".join([f"• {h}" for h in news_headlines])
            if news_headlines
            else "• 최근 관련 뉴스가 없습니다."
        )

        print(f"📰 [디버깅] 화면으로 보낼 뉴스:\n{display_news}")

        # AI 분석 호출 시 실제 수집된 news_headlines 전달
        ai_result = get_ai_investment_decision(
            TARGET_TICKER, df["Close"].iloc[-1], "trend...", news_headlines
        )

        # (중략: 매매 로직...)

        # 💡 [핵심 수정] 반환하는 딕셔너리에 display_news를 확실히 담음
        return {
            "price": int(df["Close"].iloc[-1]),
            "decision": ai_result.get("decision", "HOLD"),
            "reason": ai_result.get("reason", "분석 중..."),
            "balance": get_mock_cash_balance(token),
            "news": display_news,  # 이 값이 gui_app.py로 전달됩니다.
        }
    except Exception as e:
        return {"error": str(e)}
