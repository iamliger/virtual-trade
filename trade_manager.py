import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def execute_scalping_buy(ticker, current_price, quantity):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    total_cost = int(current_price * quantity)
    fee = int(total_cost * 0.00015)
    final_deduction = total_cost + fee
    cursor.execute("SELECT cash FROM account")
    cash_row = cursor.fetchone()
    cash = cash_row[0] if cash_row else 0

    if cash < final_deduction:
        conn.close()
        return False, "예수금 부족"

    cursor.execute("UPDATE account SET cash = cash - ?", (final_deduction,))
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
    return True, "성공"


def execute_scalping_sell(ticker, current_price, quantity):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT quantity, avg_price FROM holdings WHERE ticker = ?", (ticker,)
    )
    row = cursor.fetchone()
    if not row or row[0] < quantity:
        conn.close()
        return False, "주식 부족"

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
            profit,
        ),
    )
    conn.commit()
    conn.close()
    return True, f"수익:{profit:,}원"
