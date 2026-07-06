import sqlite3
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 광범위한 종목 후보군
TOTAL_MARKET_POOL = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "한화오션": "042660.KS",
    "카카오": "035720.KS",
    "HMM": "011200.KS",
    "대한해운": "005880.KS",
    "두산에너빌리티": "034020.KS",
    "HLB": "028300.KQ",
    "미래산업": "025560.KS",
    "대원전선": "006340.KS",
    "삼성중공업": "010140.KS",
    "신한지주": "055550.KS",
}


def get_filtered_stocks():
    """현재 예수금으로 '최소 1주'를 살 수 있는 종목만 반환"""
    conn = sqlite3.connect("virtual_trade.db")
    cash_row = conn.execute("SELECT cash FROM account").fetchone()
    conn.close()
    cash = cash_row[0] if cash_row else 0

    filtered = []
    for name, ticker in TOTAL_MARKET_POOL.items():
        try:
            # 실시간 가격 확인
            curr_p = int(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
            if curr_p < cash:  # 예수금보다 싼 종목만 추가
                filtered.append(f"{name} ({ticker})")
        except:
            continue

    return filtered if filtered else ["삼성전자 (005930.KS)"]


def predict_best_stock():
    """자본금 맞춤형 AI 추천 (100% 한글 강제)"""
    stocks = get_filtered_stocks()
    summary = f"현재 가용 자본으로 매수 가능한 종목군: {stocks}\n"
    prompt = (
        "너는 여의도 최고의 투자 전략가이다. 위 리스트 중 현재 한국 시장 상황에서 "
        "단타(Scalping) 수익을 내기에 가장 유망한 종목 1개를 골라라.\n"
        "반드시 한국어로만 대답하고, 추천 이유를 논리적으로 설명하라. 영어는 절대 쓰지 마라."
    )
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        return res["message"]["content"]
    except:
        return "예측 엔진 연결 실패"


def get_holdings_with_valuation():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute("SELECT ticker, quantity, avg_price FROM holdings").fetchall()
    conn.close()
    res = []
    for ticker, qty, avg_p in rows:
        try:
            curr_p = int(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
            profit = (curr_p - avg_p) * qty
            rate = (profit / (avg_p * qty)) * 100
            res.append((ticker, qty, avg_p, curr_p, profit, rate))
        except:
            res.append((ticker, qty, avg_p, 0, 0, 0))
    return res


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute(
        "SELECT trade_date, ticker, type, price, quantity, profit FROM trade_history ORDER BY id DESC LIMIT 15"
    ).fetchall()
    conn.close()
    return rows


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
            return {"status": "WAITING", "msg": "시세 동기화 대기 중"}

        price = int(df["Close"].iloc[-1])
        # 자산 초과 매수 시도 방지
        if price > db_cash:
            return {
                "status": "ACTIVE",
                "trade_status": "자산초과매수불가",
                "ticker": target_ticker,
                "price": price,
                "db_balance": db_cash,
                "today_profit": today_p,
                "weekly_profit": week_p,
                "monthly_profit": month_p,
                "decision": "HOLD",
                "reason": "자본금이 부족한 종목입니다.",
                "news": "없음",
                "mock_balance": 0,
            }

        history_str = " -> ".join(
            [f"{int(p):,}원" for p in df["Close"].tail(5).tolist()]
        )
        news_headlines = [n.get("title") for n in stock.news[:2] if n.get("title")]

        ai_res = get_ai_investment_decision(
            target_ticker, price, history_str, news_headlines
        )
        decision = ai_res.get("decision", "HOLD")

        # 가용 자본 전체를 투입하는 단타 전략
        qty = db_cash // (price + (price * 0.00015))
        if qty < 1:
            qty = 0

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
            "reason": ai_res.get("reason", "분석 중"),
            "news": "\n".join(news_headlines) if news_headlines else "뉴스 없음",
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "today_profit": today_p,
            "weekly_profit": week_p,
            "monthly_profit": month_p,
            "mock_balance": get_mock_cash_balance(token),
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
