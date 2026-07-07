import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 1. 계좌 정보
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS account (cash INTEGER, updated_at TEXT)"""
    )
    # 2. 보유 종목
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS holdings (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)"""
    )
    # 3. 매매 기록
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"""
    )
    # 4. AI 분석 로그
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ai_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"""
    )
    # 5. 종목 마스터 (감시 리스트 통합 관리)
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT, price INTEGER)"""
    )

    # [수정] 초기 예수금 및 종목 마스터 초기화
    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (100000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    # [수정] 종목 마스터가 비어있을 경우 초기 시드 리스트 삽입
    cursor.execute("SELECT count(*) FROM stock_master")
    if cursor.fetchone()[0] == 0:
        initial_pool = [
            ("011200.KS", "HMM"),
            ("005880.KS", "대한해운"),
            ("025560.KS", "미래산업"),
            ("006340.KS", "대원전선"),
            ("032820.KQ", "우리기술"),
            ("028670.KS", "팬오션"),
            ("010140.KS", "삼성중공업"),
            ("025820.KS", "이구산업"),
            ("004700.KS", "모나리자"),
            ("012800.KS", "대창"),
            ("102370.KQ", "케이옥션"),
        ]
        cursor.executemany(
            "INSERT INTO stock_master (ticker, name, price) VALUES (?, ?, 0)",
            initial_pool,
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
    conn.commit()
    conn.close()
    create_tables()


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
