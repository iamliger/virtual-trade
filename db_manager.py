import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def create_tables():
    """DB 초기화 및 테이블 생성"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 1. 계좌 (예수금)
    cursor.execute("""CREATE TABLE IF NOT EXISTS account 
                      (cash INTEGER, updated_at TEXT)""")
    # 2. 보유 주식
    cursor.execute("""CREATE TABLE IF NOT EXISTS holdings 
                      (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)""")
    # 3. 매매 기록
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS trade_history 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, 
                       ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"""
    )
    # 4. AI 분석 로그
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ai_log 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"""
    )
    # 5. 종목 이름 마스터
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )

    # 초기 실행 시 데이터가 없으면 100만원으로 시작 (현실적 시뮬레이션)
    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (1000000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    conn.commit()
    conn.close()


def update_cash(new_amount):
    """사용자가 원하는 시드머니로 DB 예수금 수동 업데이트"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE account SET cash = ?, updated_at = ?",
        (new_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_statistics():
    """주간 및 월간 수익 통계 계산"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 오늘 수익
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) = date('now')"
    )
    today = cursor.fetchone()[0] or 0

    # 주간 수익 (최근 7일)
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-7 days')"
    )
    weekly = cursor.fetchone()[0] or 0

    # 월간 수익 (최근 30일)
    cursor.execute(
        "SELECT SUM(profit) FROM trade_history WHERE date(trade_date) >= date('now', '-30 days')"
    )
    monthly = cursor.fetchone()[0] or 0

    conn.close()
    return today, weekly, monthly


if __name__ == "__main__":
    create_tables()
