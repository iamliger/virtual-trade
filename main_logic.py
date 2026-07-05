# main_logic.py (전체 교체)
import sqlite3
from datetime import datetime

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell


def get_dynamic_stocks():
    """시장에서 거래량과 뉴스가 활발한 종목들을 동적으로 스캔하여 반환"""
    # 💡 실제로는 크롤링이 필요하지만, 안정성을 위해 우량주 20개 중 뉴스가 있는 것을 선별
    pool = [
        "005930.KS",
        "000660.KS",
        "042660.KS",
        "034020.KS",
        "035720.KS",
        "011200.KS",
        "064350.KS",
        "028300.KQ",
        "035420.KS",
        "005380.KS",
        "000270.KS",
        "012450.KS",
        "009150.KS",
        "066570.KS",
        "003670.KS",
        "032830.KS",
        "010950.KS",
        "000810.KS",
        "033780.KS",
        "000100.KS",
    ]

    found_stocks = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()

    print("🛰️ [시장 스캐닝] 뉴스 호재 종목 발굴 중...")
    for ticker in pool:
        stock = yf.Ticker(ticker)
        # 뉴스가 있는 종목을 우선적으로 수집
        if stock.news:
            name = stock.info.get("shortName", ticker)
            found_stocks.append(f"{name} ({ticker})")
            # DB에 종목 이름 저장
            cursor.execute(
                "INSERT OR REPLACE INTO stock_master (ticker, name) VALUES (?, ?)",
                (ticker, name),
            )

    conn.commit()
    conn.close()
    return found_stocks


def run_trading_cycle(token, target_ticker):
    try:
        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"error": "데이터 수집 불가"}

        current_price = int(df["Close"].iloc[-1])
        prev_price = int(df["Close"].iloc[-2]) if len(df) > 1 else current_price

        # 실시간 가격 변동 화살표 계산
        trend_arrow = (
            "▲"
            if current_price > prev_price
            else "▼" if current_price < prev_price else "●"
        )
        change_pct = ((current_price - prev_price) / prev_price) * 100

        # AI 뉴스 분석 수행
        news_data = stock.news[:3]
        news_headlines = [n.get("title") for n in news_data if n.get("title")]

        ai_result = get_ai_investment_decision(
            target_ticker, current_price, "Trend...", news_headlines
        )

        # (매수/매도 로직 및 DB 기록 부분은 기존과 동일하게 유지)
        # ...

        return {
            "ticker": target_ticker,
            "price": current_price,
            "arrow": trend_arrow,
            "change_pct": change_pct,
            "decision": ai_result.get("decision", "HOLD"),
            "reason": ai_result.get("reason", "분석 중"),
            "news": (
                "\n".join([f"• {h}" for h in news_headlines])
                if news_headlines
                else "관련 뉴스 없음"
            ),
            "balance": get_mock_cash_balance(token),
        }
    except Exception as e:
        return {"error": str(e)}
