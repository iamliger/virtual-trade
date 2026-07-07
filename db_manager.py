import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def create_tables():
    """DB 초기화 및 테이블 구조 자동 보정"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. 기본 테이블 생성
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
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )

    # [스키마 보정] stock_master에 price 컬럼이 없는 구버전일 경우 컬럼 추가
    try:
        cursor.execute("SELECT price FROM stock_master LIMIT 1")
    except sqlite3.OperationalError:
        print("🔧 [DB] 구버전 스키마 감지: stock_master에 price 컬럼을 추가합니다.")
        cursor.execute("ALTER TABLE stock_master ADD COLUMN price INTEGER DEFAULT 0")

    # 초기 데이터 설정
    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (100000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    # 종목 마스터 초기화 (기존 데이터 삭제 후 최신화)
    cursor.execute("SELECT count(*) FROM stock_master")
    if cursor.fetchone()[0] <= 1:  # 데이터가 없거나 기본값만 있을 때
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
            "INSERT OR REPLACE INTO stock_master (ticker, name, price) VALUES (?, ?, 0)",
            initial_pool,
        )

    conn.commit()
    conn.close()
    print("✅ [DB] 테이블 체크 및 최신화 완료")


def reset_db_completely():
    """모든 기록 초기화 및 재시작"""
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
