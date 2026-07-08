# trade_manager.py
import sqlite3
from datetime import datetime

import yfinance as yf

DB_FILE = "virtual_trade.db"


def execute_scalping_buy(ticker, current_price, quantity):
    if quantity <= 0:
        return False
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    total_cost = int(current_price * quantity)
    fee = int(total_cost * 0.00015)
    cursor.execute("SELECT cash FROM account")
    cash = cursor.fetchone()[0]
    if cash < (total_cost + fee):
        return False

    cursor.execute("UPDATE account SET cash = cash - ?", (total_cost + fee,))
    cursor.execute(
        "SELECT quantity, avg_price FROM holdings WHERE ticker = ?", (ticker,)
    )
    row = cursor.fetchone()
    if row:
        new_qty = row[0] + quantity
        new_avg = int(((row[1] * row[0]) + (current_price * quantity)) / new_qty)
        cursor.execute(
            "UPDATE holdings SET quantity = ?, avg_price = ? WHERE ticker = ?",
            (new_qty, new_avg, ticker),
        )
    else:
        cursor.execute(
            "INSERT INTO holdings VALUES (?, ?, ?)", (ticker, quantity, current_price)
        )

    cursor.execute(
        "INSERT INTO trade_history (trade_date, ticker, type, price, quantity, profit) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ticker,
            "매수",
            current_price,
            quantity,
            0,
        ),
    )
    conn.commit()
    conn.close()
    return True


def execute_scalping_sell(ticker, current_price, quantity):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT quantity, avg_price FROM holdings WHERE ticker = ?", (ticker,)
    )
    row = cursor.fetchone()
    if not row or row[0] < quantity:
        return False

    total_sales = int(current_price * quantity)
    fee_tax = int(total_sales * (0.00015 + 0.0018))
    profit = (total_sales - fee_tax) - (row[1] * quantity)
    cursor.execute("UPDATE account SET cash = cash + ?", (total_sales - fee_tax,))
    if row[0] == quantity:
        cursor.execute("DELETE FROM holdings WHERE ticker = ?", (ticker,))
    else:
        cursor.execute(
            "UPDATE holdings SET quantity = quantity - ? WHERE ticker = ?",
            (quantity, ticker),
        )

    cursor.execute(
        "INSERT INTO trade_history (trade_date, ticker, type, price, quantity, profit) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ticker,
            "매도",
            current_price,
            quantity,
            int(profit),
        ),
    )
    conn.commit()
    conn.close()
    return True


def force_exit_all_stocks():
    """모든 주식 전량 매도"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, quantity FROM holdings")
    holdings = cursor.fetchall()
    conn.close()
    count = 0
    for t, q in holdings:
        try:
            cp = int(yf.Ticker(t).history(period="1d")["Close"].iloc[-1])
            if execute_scalping_sell(t, cp, q):
                count += 1
        except:
            continue
    return count
