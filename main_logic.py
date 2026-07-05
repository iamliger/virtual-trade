# main_logic.py (전체 교체)
import sqlite3
from datetime import datetime

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell


def setup_db():
    """프로그램 시작 전 필요한 테이블을 자동으로 생성"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS daily_goals (date TEXT PRIMARY KEY, target_profit INTEGER, current_profit INTEGER)"""
    )
    conn.commit()
    conn.close()


def get_dynamic_stocks():
    """뉴스가 있고 거래가 활발한 1~5만원대 소액 단타용 종목 발굴"""
    setup_db()
    # 단타에 적합한 활동성 종목 풀
    pool = [
        "042660.KS",
        "034020.KS",
        "011200.KS",
        "064350.KS",
        "028300.KQ",
        "091990.KQ",
        "102710.KS",
        "003670.KS",
        "035720.KS",
    ]

    found_stocks = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()

    for ticker in pool:
        stock = yf.Ticker(ticker)
        name = stock.info.get("shortName", ticker)
        # DB에 이름 저장
        cursor.execute(
            "INSERT OR REPLACE INTO stock_master (ticker, name) VALUES (?, ?)",
            (ticker, name),
        )
        found_stocks.append(f"{name} ({ticker})")

    conn.commit()
    conn.close()
    return found_stocks


def run_trading_cycle(token, target_ticker, target_profit_goal):
    try:
        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"error": "데이터 수집 불가"}

        current_price = int(df["Close"].iloc[-1])
        prev_price = int(df["Close"].iloc[-2]) if len(df) > 1 else current_price

        # 실시간 변동 시각화 데이터
        trend_arrow = (
            "▲"
            if current_price > prev_price
            else "▼" if current_price < prev_price else "●"
        )
        change_pct = ((current_price - prev_price) / prev_price) * 100

        # AI 분석
        news_data = stock.news[:3]
        news_headlines = [n.get("title") for n in news_data if n.get("title")]
        ai_result = get_ai_investment_decision(
            target_ticker, current_price, "Trend...", news_headlines
        )

        decision = ai_result.get("decision", "HOLD")

        # [핵심] 10~50만원 소액 단타 로직
        # 한 번 매수 시 약 30만원 정도로 설정
        buy_quantity = 300000 // current_price
        if buy_quantity < 1:
            buy_quantity = 1

        if decision == "BUY":
            execute_scalping_buy(target_ticker, current_price, buy_quantity)
        elif decision == "SELL":
            execute_scalping_sell(target_ticker, current_price, buy_quantity)

        return {
            "ticker_name": target_ticker,  # 이후 GUI에서 이름으로 매칭
            "price": current_price,
            "arrow": trend_arrow,
            "change_pct": change_pct,
            "decision": decision,
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
