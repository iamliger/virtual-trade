# main_logic.py
import sqlite3
from datetime import datetime

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 1. 감시 및 추천 후보 종목 리스트
WATCH_LIST = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "에코프로비엠": "247540.KQ",
}


def run_trading_cycle(token, target_ticker):
    """
    선택된 종목에 대해 1분간의 매매 사이클을 수행합니다.
    모든 결과는 DB에 기록되어 수익률 증명의 근거가 됩니다.
    """
    try:
        # 1. 데이터 수집 (주가)
        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")

        if df.empty:
            return {"error": f"{target_ticker} 데이터를 가져오지 못했습니다."}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        # 2. 데이터 수집 (뉴스)
        raw_news = stock.news[:3] if stock.news else []
        news_headlines = [item.get("title") for item in raw_news if item.get("title")]
        display_news = (
            "\n".join([f"• {h}" for h in news_headlines])
            if news_headlines
            else "• 최근 관련 뉴스가 없습니다."
        )

        # 3. AI 판단 의뢰
        ai_result = get_ai_investment_decision(
            target_ticker, current_price, price_history_str, news_headlines
        )
        decision = ai_result.get("decision", "HOLD")
        reason = ai_result.get("reason", "분석 실패")

        # 4. 가상 매매 실행 (10주 단위 단타 설정)
        if decision == "BUY":
            execute_scalping_buy(target_ticker, current_price, quantity=10)
        elif decision == "SELL":
            execute_scalping_sell(target_ticker, current_price, quantity=10)

        # 5. AI 판단 기록 (DB 저장 - 복기용)
        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_log (log_date, ticker, decision, reason) VALUES (?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                target_ticker,
                decision,
                reason,
            ),
        )
        conn.commit()
        conn.close()

        # 6. 최종 결과 묶어서 반환
        return {
            "ticker": target_ticker,
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": display_news,
            "balance": get_mock_cash_balance(token),
        }

    except Exception as e:
        return {"error": str(e)}
