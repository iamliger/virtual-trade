import sqlite3
import time
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# 1. 시장 스캔 후보군 (변동성 우량주)
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


def setup_db():
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
    """시장의 종목들을 DB에 등록하고 리스트 반환"""
    setup_db()
    found_stocks = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    for name, ticker in SCAN_POOL.items():
        cursor.execute(
            "INSERT OR REPLACE INTO stock_master (ticker, name) VALUES (?, ?)",
            (ticker, name),
        )
        found_stocks.append(f"{name} ({ticker})")
    conn.commit()
    conn.close()
    return found_stocks


def predict_best_stock():
    """[핵심] 프로그램 시작 시 시장 뉴스를 분석하여 오늘 유망한 종목을 추천"""
    summary = ""
    for name, ticker in SCAN_POOL.items():
        stock = yf.Ticker(ticker)
        news = stock.news[:1]
        headline = news[0].get("title", "특이사항 없음") if news else "특이사항 없음"
        summary += f"- {name}({ticker}): {headline}\n"

    prompt = f"다음은 오늘 한국 시장 주요 종목 뉴스이다:\n{summary}\n이 뉴스들을 분석해서 오늘 단타 수익(scalping) 가능성이 가장 높은 종목 1개만 골라 '종목명(코드)'과 '선정이유'를 한국어로 짧고 명확하게 보고해줘."

    try:
        response = ollama.chat(
            model="llama3", messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except:
        return "종목 예측 엔진 연결 실패"


def run_trading_cycle(token, target_ticker, target_profit_goal):
    """실시간 주가/뉴스 분석 및 매매 루프"""
    try:
        now = datetime.now()
        # 장 마감 전 자동 청산 (오후 3시 20분 ~ 3시 30분)
        is_closing_time = now.hour == 15 and 20 <= now.minute <= 30

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"error": "데이터 수집 불가"}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        prev_price = int(df["Close"].iloc[-2]) if len(df) > 1 else current_price
        trend_arrow = (
            "▲"
            if current_price > prev_price
            else "▼" if current_price < prev_price else "●"
        )
        change_pct = ((current_price - prev_price) / prev_price) * 100

        news_data = stock.news[:3] if stock.news else []
        news_headlines = [n.get("title") for n in news_data if n.get("title")]
        display_news = (
            "\n".join([f"• {h}" for h in news_headlines])
            if news_headlines
            else "• 최근 관련 뉴스 없음"
        )

        if is_closing_time:
            decision = "SELL"
            reason = "🔔 장 마감 전 수익 확정을 위한 자동 일괄 매도 단계입니다."
        else:
            ai_result = get_ai_investment_decision(
                target_ticker, current_price, price_history_str, news_headlines
            )
            decision = ai_result.get("decision", "HOLD")
            reason = ai_result.get("reason", "분석 중")

        # 소액 단타 (약 30만원 규모)
        buy_quantity = 300000 // current_price
        if buy_quantity < 1:
            buy_quantity = 1

        trade_status = "IDLE"
        if decision == "BUY":
            if execute_scalping_buy(target_ticker, current_price, buy_quantity):
                trade_status = f"매수성공({buy_quantity}주)"
        elif decision == "SELL":
            if execute_scalping_sell(target_ticker, current_price, buy_quantity):
                trade_status = f"매도성공({buy_quantity}주)"

        return {
            "ticker": target_ticker,
            "price": current_price,
            "arrow": trend_arrow,
            "change_pct": change_pct,
            "decision": decision,
            "reason": reason,
            "news": display_news,
            "balance": get_mock_cash_balance(token),
            "trade_status": trade_status,
        }
    except Exception as e:
        return {"error": str(e)}
