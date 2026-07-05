# main_logic.py
import sqlite3
from datetime import datetime

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell


def setup_db():
    """DB 초기화 및 테이블 생성"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ai_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"""
    )
    conn.commit()
    conn.close()


def get_dynamic_stocks():
    """실시간으로 뉴스 호재가 있는 단타용 종목 발굴"""
    setup_db()
    # 단타에 적합한 활동성 종목 풀
    pool = [
        "042660.KS",
        "034020.KS",
        "011200.KS",
        "064350.KS",
        "028300.KQ",
        "035720.KS",
        "091990.KQ",
    ]
    found_stocks = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()

    for ticker in pool:
        try:
            stock = yf.Ticker(ticker)
            name = stock.info.get("shortName", ticker)
            cursor.execute(
                "INSERT OR REPLACE INTO stock_master (ticker, name) VALUES (?, ?)",
                (ticker, name),
            )
            found_stocks.append(f"{name} ({ticker})")
        except:
            continue

    conn.commit()
    conn.close()
    return found_stocks


def run_trading_cycle(token, target_ticker, target_profit_goal):
    """1분 주기 매매 사이클 수행 (장 마감 자동 매도 포함)"""
    try:
        # 한국 시간 기준 장 마감 체크 (오후 3시 20분 ~ 3시 30분)
        now = datetime.now()
        is_closing_time = now.hour == 15 and 20 <= now.minute <= 30

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"error": "데이터 수집 실패"}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        # 뉴스 수집 및 분석
        news_data = stock.news[:3] if stock.news else []
        news_headlines = [n.get("title") for n in news_data if n.get("title")]
        display_news = (
            "\n".join([f"• {h}" for h in news_headlines])
            if news_headlines
            else "• 최근 관련 뉴스 없음"
        )

        # 장 마감 시간 시 강제 매도, 아니면 AI 판단
        if is_closing_time:
            decision = "SELL"
            reason = "🔔 장 마감 전 수익 확정을 위한 자동 일괄 매도 단계입니다."
        else:
            ai_result = get_ai_investment_decision(
                target_ticker, current_price, price_history_str, news_headlines
            )
            decision = ai_result.get("decision", "HOLD")
            reason = ai_result.get("reason", "분석 중")

        # 10~50만원 소액 단타 (약 30만원 규모 매수)
        buy_quantity = 300000 // current_price
        if buy_quantity < 1:
            buy_quantity = 1

        trade_status = "IDLE"
        if decision == "BUY":
            if execute_scalping_buy(target_ticker, current_price, buy_quantity):
                trade_status = "BUY_SUCCESS"
        elif decision == "SELL":
            if execute_scalping_sell(target_ticker, current_price, buy_quantity):
                trade_status = "SELL_SUCCESS"

        return {
            "ticker": target_ticker,
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": display_news,
            "balance": get_mock_cash_balance(token),
            "trade_status": trade_status,
        }
    except Exception as e:
        return {"error": str(e)}
