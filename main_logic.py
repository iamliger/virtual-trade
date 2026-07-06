import sqlite3
import time
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 동적 시장 스캔 후보
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
    """시장의 뉴스를 먼저 읽고 오늘의 대장주를 선정"""
    summary = "현재 시장 주요 소식:\n"
    for name, ticker in SCAN_POOL.items():
        try:
            stock = yf.Ticker(ticker)
            news = stock.news[:1]
            title = news[0].get("title", "특이사항 없음") if news else "뉴스 없음"
            summary += f"- {name}: {title}\n"
        except:
            continue

    prompt = f"너는 여의도 최고의 전략가이다. 아래 데이터를 분석해서 오늘 단타로 가장 유망한 종목 1개를 골라 한글로 이유와 함께 보고하라. 영어는 절대 쓰지 마라.\n{summary}"
    try:
        res = ollama.chat(
            model="llama3", messages=[{"role": "user", "content": prompt}]
        )
        return res["message"]["content"]
    except:
        return "예측 엔진 일시 오류"


def get_db_history():
    """최신 매매 기록 10건 조회"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trade_date, ticker, type, price, profit FROM trade_history ORDER BY id DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_holdings():
    """현재 내가 들고 있는 주식 현황 조회"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, quantity, avg_price FROM holdings")
    rows = cursor.fetchall()
    conn.close()
    return rows


def run_trading_cycle(token, target_ticker):
    """1분 주기 매매 로직"""
    try:
        now = datetime.now()
        stock = yf.Ticker(target_ticker)
        # 통신 에러 방지용 재시도 로직
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "API 데이터 동기화 대기 중..."}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])
        news_data = stock.news[:2]
        news_headlines = [n.get("title") for n in news_data if n.get("title")]

        # AI 판단
        ai_res = get_ai_investment_decision(
            target_ticker, current_price, price_history_str, news_headlines
        )
        decision = ai_res.get("decision", "HOLD")
        reason = ai_res.get("reason", "데이터 분석 중")

        # 단타 수량 설정 (약 50만원 규모)
        qty = 500000 // current_price
        if qty < 1:
            qty = 1

        trade_msg = "대기"
        if decision == "BUY":
            success, msg = execute_scalping_buy(target_ticker, current_price, qty)
            trade_msg = f"매수 {msg}" if success else f"매수 실패({msg})"
        elif decision == "SELL":
            success, msg = execute_scalping_sell(target_ticker, current_price, qty)
            trade_msg = f"매도 {msg}" if success else f"매도 실패({msg})"

        # DB 잔고 조회
        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cursor.execute("SELECT cash FROM account")
        db_cash = cursor.fetchone()[0]
        conn.close()

        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": "\n".join(news_headlines) if news_headlines else "뉴스 없음",
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "mock_balance": get_mock_cash_balance(token),
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
