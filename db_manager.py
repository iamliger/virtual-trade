# db_manager.py
import sqlite3
from datetime import datetime

import config

DB_FILE = "virtual_trade.db"


def create_tables():
    """데이터베이스 초기화 및 스키마 자동 보정"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS account (cash INTEGER, updated_at TEXT)")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS holdings (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ai_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT, price INTEGER)"
    )

    # 스키마 보정: price 컬럼 유무 확인
    try:
        cursor.execute("SELECT price FROM stock_master LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE stock_master ADD COLUMN price INTEGER DEFAULT 0")

    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (config.DEFAULT_SEED_MONEY, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    # 검증된 우량 저가주 마스터 리스트 초기화
    cursor.execute("SELECT count(*) FROM stock_master")
    if cursor.fetchone()[0] <= 1:
        pool = [
            ("011200.KS", "HMM", 0),
            ("005880.KS", "대한해운", 0),
            ("006340.KS", "대원전선", 0),
            ("032820.KQ", "우리기술", 0),
            ("028670.KS", "팬오션", 0),
            ("010140.KS", "삼성중공업", 0),
            ("025820.KS", "이구산업", 0),
            ("004700.KS", "모나리자", 0),
            ("012800.KS", "대창", 0),
            ("102370.KQ", "케이옥션", 0),
            ("035890.KQ", "서희건설", 0),
        ]
        cursor.executemany("INSERT OR REPLACE INTO stock_master VALUES (?, ?, ?)", pool)

    conn.commit()
    conn.close()


def reset_db_completely():
    """DB 초기화"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for table in ["account", "holdings", "trade_history", "ai_log", "stock_master"]:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    conn.close()
    create_tables()


def update_cash(new_amount):
    """예수금 수동 업데이트"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "UPDATE account SET cash = ?, updated_at = ?",
        (new_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_statistics():
    """오늘의 수익 통계 계산"""
    conn = sqlite3.connect(DB_FILE)
    today = (
        conn.execute(
            "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) = date('now', 'localtime')"
        ).fetchone()[0]
        or 0
    )
    weekly = (
        conn.execute(
            "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-7 days', 'localtime')"
        ).fetchone()[0]
        or 0
    )
    monthly = (
        conn.execute(
            "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-30 days', 'localtime')"
        ).fetchone()[0]
        or 0
    )
    conn.close()
    return today, weekly, monthly
