import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def create_tables():
    """DB 초기화 및 테이블 생성 (예수금 강제 설정 포함)"""
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

    # [핵심] 예수금이 없으면 5,000만원 강제 입금
    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO account VALUES (?, ?)",
            (50000000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    conn.commit()
    conn.close()
    print("✅ [DB] 시스템 초기화 및 가상 자산 5,000만원 입금 완료")


def reset_db():
    """DB 전체 초기화 기능"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS account")
    cursor.execute("DROP TABLE IF EXISTS holdings")
    cursor.execute("DROP TABLE IF EXISTS trade_history")
    cursor.execute("DROP TABLE IF EXISTS ai_log")
    conn.commit()
    conn.close()
    create_tables()


if __name__ == "__main__":
    create_tables()
