import sqlite3


def create_tables():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    # 1. 현금 계좌
    cursor.execute("""CREATE TABLE IF NOT EXISTS account 
                      (cash INTEGER, updated_at TEXT)""")
    # 2. 보유 종목
    cursor.execute("""CREATE TABLE IF NOT EXISTS holdings 
                      (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)""")
    # 3. 매매 히스토리
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
    # 5. 종목 마스터
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )

    # 초기 예수금 5천만원 설정 (데이터가 없을 때만)
    cursor.execute("SELECT count(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account VALUES (?, datetime('now'))", (50000000,))

    conn.commit()
    conn.close()
    print("✅ DB 테이블 및 초기화 완료")


if __name__ == "__main__":
    create_tables()
