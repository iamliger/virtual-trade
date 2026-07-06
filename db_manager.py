import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS account (cash INTEGER, updated_at TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS holdings (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ai_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT, price INTEGER)"""
    )

    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (100000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
    conn.commit()
    conn.close()


def reset_db_completely():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM account")
    cursor.execute("DELETE FROM holdings")
    cursor.execute("DELETE FROM trade_history")
    cursor.execute("DELETE FROM ai_log")
    cursor.execute("DELETE FROM stock_master")
    cursor.execute(
        "INSERT INTO account VALUES (?, ?)",
        (100000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def update_cash(new_amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE account SET cash = ?, updated_at = ?",
        (new_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_statistics():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) = date('now', 'localtime')"
    )
    today = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-7 days', 'localtime')"
    )
    weekly = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-30 days', 'localtime')"
    )
    monthly = cursor.fetchone()[0] or 0
    conn.close()
    return today, weekly, monthly


if __name__ == "__main__":
    create_tables()
