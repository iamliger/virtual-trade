import sqlite3
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import ai_discover_new_stocks, get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 404 에러 종목(017040.KS 등)을 제외한 신뢰 리스트
CLEAN_POOL = [
    "HMM:011200.KS",
    "대한해운:005880.KS",
    "미래산업:025560.KS",
    "대원전선:006340.KS",
    "우리기술:032820.KQ",
    "팬오션:028670.KS",
    "삼성중공업:010140.KS",
    "이구산업:025820.KS",
    "모나리자:004700.KS",
    "대창:012800.KS",
    "케이옥션:102370.KQ",
]


def refresh_stock_pool_by_capital():
    conn = sqlite3.connect("virtual_trade.db")
    cash = conn.execute("SELECT cash FROM account").fetchone()[0]
    conn.close()

    ai_raw = ai_discover_new_stocks(cash, ",".join(CLEAN_POOL))
    discovered = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_master")

    for line in ai_raw.split("\n"):
        if ":" in line:
            try:
                name, ticker = line.split(":")[-2:]
                ticker = ticker.strip()
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                if not hist.empty:
                    price = int(hist["Close"].iloc[-1])
                    if price <= cash:
                        cursor.execute(
                            "INSERT OR REPLACE INTO stock_master VALUES (?, ?, ?)",
                            (ticker, name, price),
                        )
                        discovered.append(f"{name} ({ticker})")
            except:
                continue
    conn.commit()
    conn.close()
    return discovered if discovered else ["대한해운 (005880.KS)"]


def predict_market_view():
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute("SELECT name, ticker FROM stock_master LIMIT 5").fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    prompt = f"너는 한국 수석 전략가이다. 반드시 한글로만 대답하라. 시작은 '[시장분석]'으로 하라.\n대상:\n{summary}"
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        return res["message"]["content"]
    except:
        return "예측 엔진 일시 오류"


def get_db_holdings():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute("SELECT ticker, quantity, avg_price FROM holdings").fetchall()
    conn.close()
    res = []
    for t, q, a in rows:
        try:
            cp = int(yf.Ticker(t).history(period="1d")["Close"].iloc[-1])
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((t, q, a, cp, profit, rate))
        except:
            res.append((t, q, a, 0, 0, 0))
    return res


def run_trading_cycle(token, target_ticker, daily_goal):
    try:
        today_p, week_p, month_p = get_statistics()
        conn = sqlite3.connect("virtual_trade.db")
        db_cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()
        if today_p >= daily_goal:
            return {
                "status": "GOAL_REACHED",
                "today_profit": today_p,
                "db_balance": db_cash,
            }

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "시세 대기 중"}

        price = int(df["Close"].iloc[-1])
        if price > db_cash:
            return {
                "status": "ACTIVE",
                "trade_status": "자산부족",
                "ticker": target_ticker,
                "price": price,
                "db_balance": db_cash,
                "today_profit": today_p,
                "weekly_profit": week_p,
                "monthly_profit": month_p,
                "decision": "HOLD",
                "reason": "자본금 부족",
                "news": "없음",
                "mock_balance": 0,
            }

        history_str = " -> ".join(
            [f"{int(p):,}원" for p in df["Close"].tail(5).tolist()]
        )
        ai_res = get_ai_investment_decision(target_ticker, price, history_str, [])
        decision = ai_res.get("decision", "HOLD")
        qty = db_cash // (price + (price * 0.001))

        trade_msg = "관망"
        if decision == "BUY" and qty > 0:
            success, msg = execute_scalping_buy(target_ticker, price, qty)
            trade_msg = f"매수 {msg}"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (target_ticker,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
                success, msg = execute_scalping_sell(target_ticker, price, hold_qty[0])
                trade_msg = f"매도 {msg}"

        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": price,
            "decision": decision,
            "reason": ai_res.get("reason", "분석중"),
            "news": "없음",
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "today_profit": today_p,
            "weekly_profit": week_p,
            "monthly_profit": month_p,
            "mock_balance": get_mock_cash_balance(token),
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
