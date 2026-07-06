import sqlite3
import time
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

SCAN_POOL = {
    "한화오션": "042660.KS",
    "두산에너빌리티": "034020.KS",
    "HMM": "011200.KS",
    "현대로템": "064350.KS",
    "HLB": "028300.KQ",
    "카카오": "035720.KS",
    "SK하이닉스": "000660.KS",
    "삼성전자": "005930.KS",
}


def predict_best_stock():
    summary = "현재 시장 주요 동향:\n"
    for name, ticker in SCAN_POOL.items():
        try:
            stock = yf.Ticker(ticker)
            news = stock.news[:1]
            title = news[0].get("title", "소식 없음") if news else "소식 없음"
            summary += f"- {name}: {title}\n"
        except:
            continue
    prompt = f"너는 한국 최고의 주식 전략가이다. 아래 데이터를 분석해 오늘 단타 수익이 유망한 종목 1개를 골라 한글로 이유와 함께 보고하라. 영어 금지.\n{summary}"
    try:
        res = ollama.chat(
            model="llama3", messages=[{"role": "user", "content": prompt}]
        )
        return res["message"]["content"]
    except:
        return "예측 엔진 연결 실패"


def get_holdings():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, quantity, avg_price FROM holdings")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trade_date, ticker, type, price, profit FROM trade_history ORDER BY id DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def run_trading_cycle(token, target_ticker, daily_goal):
    try:
        today_profit, weekly_profit, monthly_profit = get_statistics()
        if today_profit >= daily_goal:
            return {"status": "GOAL_REACHED", "today_profit": today_profit}

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "API 데이터 동기화 대기 중..."}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])
        news_headlines = [n.get("title") for n in stock.news[:2] if n.get("title")]

        ai_res = get_ai_investment_decision(
            target_ticker, current_price, price_history_str, news_headlines
        )
        decision = ai_res.get("decision", "HOLD")

        qty = 300000 // current_price
        if qty < 1:
            qty = 1

        trade_msg = "관망"
        if decision == "BUY":
            success, msg = execute_scalping_buy(target_ticker, current_price, qty)
            trade_msg = f"매수 {msg}" if success else f"매수 실패({msg})"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (target_ticker,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
                success, msg = execute_scalping_sell(
                    target_ticker, current_price, hold_qty[0]
                )
                trade_msg = f"매도 {msg}" if success else f"매도 실패({msg})"

        conn = sqlite3.connect("virtual_trade.db")
        db_cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()

        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": current_price,
            "decision": decision,
            "reason": ai_res.get("reason", "분석 중"),
            "news": "\n".join(news_headlines) if news_headlines else "뉴스 없음",
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "mock_balance": get_mock_cash_balance(token),
            "today_profit": today_profit,
            "weekly_profit": weekly_profit,
            "monthly_profit": monthly_profit,
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
