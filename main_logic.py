import logging
import re
import sqlite3
from datetime import datetime

import ollama
import requests
import yfinance as yf

import config
from ai_brain import ai_discover_new_stocks, get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance

# 💡 파트너님이 완성하신 고성능 뉴스 모듈을 임포트합니다.
from news_crawler import get_naver_stock_news


def check_ollama_status():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def get_market_indices():
    try:
        kospi = yf.Ticker("^KS11").history(period="1d", timeout=config.TIMEOUT)
        kosdaq = yf.Ticker("^KQ11").history(period="1d", timeout=config.TIMEOUT)
        kp = kospi["Close"].iloc[-1]
        kp_open = kospi["Open"].iloc[0]
        kp_c = ((kp - kp_open) / kp_open * 100) if kp_open != 0 else 0.0
        kd = kosdaq["Close"].iloc[-1]
        kd_open = kosdaq["Open"].iloc[0]
        kd_c = ((kd - kd_open) / kd_open * 100) if kd_open != 0 else 0.0
        return f"KOSPI: {kp_c:+.2f}% | KOSDAQ: {kd_c:+.2f}%"
    except:
        return "지수 업데이트 중..."


def refresh_stock_pool_by_capital():
    try:
        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cash = cursor.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()

        # 임시 리스트 (나중에 DB화 가능)
        POOL = [
            "HMM:011200.KS",
            "대한해운:005880.KS",
            "미래산업:025560.KS",
            "대원전선:006340.KS",
            "우리기술:032820.KQ",
            "대창:012800.KS",
        ]
        ai_raw = ai_discover_new_stocks(cash, ",".join(POOL))
        ticker_codes = re.findall(r"(\d{6}\.K[SQ])", ai_raw)

        discovered = []
        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stock_master")
        for ticker in list(set(ticker_codes)):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d", timeout=config.TIMEOUT)
                if not hist.empty:
                    price = int(hist["Close"].iloc[-1])
                    if price <= cash:
                        name = stock.info.get("shortName", ticker)
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
    except:
        return ["대한해운 (005880.KS)"]


def predict_market_view():
    try:
        conn = sqlite3.connect("virtual_trade.db")
        stocks = conn.execute(
            "SELECT name, ticker FROM stock_master WHERE price > 0 LIMIT 3"
        ).fetchall()
        conn.close()
        summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
        indices = get_market_indices()
        prompt = f"너는 한국 수석 전략가이다. 한국어로 지수 {indices}와 종목 {summary}를 분석하라. 영어 금지."
        res = ollama.chat(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        reply = res["message"]["content"].strip()
        return (
            reply
            if not re.search("[a-zA-Z]{20,}", reply)
            else "지수 변동성을 고려한 대응을 추천합니다."
        )
    except:
        return "분석 엔진 연결 지연"


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute(
        """SELECT t.trade_date, m.name, t.type, t.price, t.quantity, t.profit 
                           FROM trade_history t LEFT JOIN stock_master m ON t.ticker = m.ticker 
                           ORDER BY t.id DESC LIMIT 20"""
    ).fetchall()
    conn.close()
    return rows


def get_db_holdings_with_names():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute(
        "SELECT m.name, h.ticker, h.quantity, h.avg_price FROM holdings h LEFT JOIN stock_master m ON h.ticker = m.ticker"
    ).fetchall()
    conn.close()
    res = []
    for n, t, q, a in rows:
        try:
            cp = int(
                yf.Ticker(t)
                .history(period="1d", timeout=config.TIMEOUT)["Close"]
                .iloc[-1]
            )
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((n if n else t, t, q, a, cp, profit, rate))
        except:
            res.append((n if n else t, t, q, a, 0, 0, 0))
    return res


def run_trading_cycle(token, target_ticker, daily_goal):
    try:
        today_p, week_p, month_p = get_statistics()
        conn = sqlite3.connect("virtual_trade.db")
        db_cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()
        if daily_goal > 0 and today_p >= daily_goal:
            return {
                "status": "GOAL_REACHED",
                "today_profit": today_p,
                "db_balance": db_cash,
            }

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "시세 동기화 대기 중"}

        price = int(df["Close"].iloc[-1])
        chart_data = df["Close"].tail(30).tolist()
        qty = int((db_cash * config.TRADE_RATIO) // (price + (price * 0.0015)))

        if qty < 1:
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
                "reason": "매수 불가",
                "news": "없음",
                "chart": chart_data,
            }

        # 💡 [파트너님의 신규 모듈 적용]
        ticker_name = re.sub(r"\(.*\)", "", target_ticker).strip()
        news = get_naver_stock_news(ticker_name, target_ticker)

        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "분석완료", [], news, indices
        )
        decision = ai_res.get("decision", "HOLD")

        trade_msg = "관망"
        if decision == "BUY" and qty > 0:
            from trade_manager import execute_scalping_buy

            if execute_scalping_buy(target_ticker, price, qty):
                trade_msg = f"매수성공({qty}주)"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (target_ticker,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
                from trade_manager import execute_scalping_sell

                if execute_scalping_sell(target_ticker, price, hold_qty[0]):
                    trade_msg = f"매도성공({hold_qty[0]}주)"

        updated_today_p, _, _ = get_statistics()
        news_report = (
            "[네이버 실시간 속보]\n" + "\n".join([f"• {h}" for h in news])
            if news
            else "[뉴스 지연 중]"
        )
        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": price,
            "decision": decision,
            "reason": ai_res.get("reason", "분석중"),
            "news": news_report,
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "today_profit": updated_today_p,
            "weekly_profit": week_p,
            "monthly_profit": month_p,
            "chart": chart_data,
            "indices": indices,
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
