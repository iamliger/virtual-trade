import logging
import sqlite3
from datetime import datetime

import config

logging.basicConfig(
    filename=config.LOG_FILE, level=config.LOG_LEVEL, format=config.LOG_FORMAT
)
DB_FILE = "virtual_trade.db"


def create_tables():
    """DB 초기화 및 테이블 구조 자동 보정"""
    try:
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

        # 스키마 보정 (price 컬럼 체크)
        try:
            cursor.execute("SELECT price FROM stock_master LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(
                "ALTER TABLE stock_master ADD COLUMN price INTEGER DEFAULT 0"
            )

        cursor.execute("SELECT count(*) FROM account")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO account VALUES (?, ?)",
                (
                    config.DEFAULT_SEED_MONEY,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"DB 초기화 실패: {e}")


def reset_db_completely():
    """[핵심] gui_app.py에서 호출하는 리셋 함수"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS account")
        cursor.execute("DROP TABLE IF EXISTS holdings")
        cursor.execute("DROP TABLE IF EXISTS trade_history")
        cursor.execute("DROP TABLE IF EXISTS ai_log")
        cursor.execute("DROP TABLE IF EXISTS stock_master")
        conn.commit()
        conn.close()
        create_tables()
        logging.info("DB 전체 리셋 완료")
    except sqlite3.Error as e:
        logging.error(f"DB 리셋 실패: {e}")


def update_cash(new_amount):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE account SET cash = ?, updated_at = ?",
            (new_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"예수금 업데이트 실패: {e}")


def get_statistics():
    try:
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
    except:
        return 0, 0, 0
