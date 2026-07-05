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
    """
    GUI에서 1분마다 호출할 매매 한 사이클 함수.
    수행 결과를 딕셔너리 형태로 반환하여 화면에 표시합니다.
    """
    try:
        # 1. 주가 및 뉴스 수집
        stock = yf.Ticker(TARGET_TICKER)
        df = stock.history(period="1d", interval="1m")

        # [디버깅] 뉴스 수집 시도 로그
        news_data = stock.news[:3] if stock.news else []
        print(f"📰 [디버깅] 수집된 뉴스 개수: {len(news_data)}개")

        news_headlines = []
        for item in news_data:
            t = item.get("title")
            if t:
                news_headlines.append(t)
                print(f"   - 뉴스 제목: {t[:30]}...")  # 뉴스 제목 출력

        if not news_headlines:
            news_headlines = ["최근 관련 뉴스가 없습니다."]

        if df.empty:
            return {"error": "시장 데이터를 가져올 수 없습니다."}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        # 2. AI 판단 (기존 코드와 동일)
        ai_result = get_ai_investment_decision(
            TARGET_TICKER, current_price, price_history_str, news_headlines
        )
        decision = ai_result.get("decision")
        reason = ai_result.get("reason")

        # [추가] AI 판단 결과 DB에 기록하기
        import sqlite3

        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_log (log_date, ticker, decision, reason) VALUES (?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                TARGET_TICKER,
                decision,
                reason,
            ),
        )
        conn.commit()
        conn.close()

        # 3. 매매 실행 (가상 계좌 반영)
        if decision == "BUY":
            execute_scalping_buy(TARGET_TICKER, current_price, TRADE_QUANTITY)
        elif decision == "SELL":
            execute_scalping_sell(TARGET_TICKER, current_price, TRADE_QUANTITY)

        # 4. 증권사 서버 잔고 확인
        mock_balance = get_mock_cash_balance(token)

        # GUI로 보낼 결과 묶음
        return {
            "price": current_price,
            "history": price_history_str,
            "decision": decision,
            "reason": reason,
            "balance": mock_balance,
            "news": "\n".join([f"• {h}" for h in news_headlines]),
        }

    except Exception as e:
        return {"error": str(e)}
